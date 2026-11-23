/**
 * jsonrpc.js - JSON-RPC 2.0 helpers shared by the stdio and HTTP transports.
 */

const { StringDecoder } = require('string_decoder');

const RPC_ERRORS = {
  PARSE_ERROR: -32700,
  INVALID_REQUEST: -32600,
  METHOD_NOT_FOUND: -32601,
  INVALID_PARAMS: -32602,
  INTERNAL_ERROR: -32603
};

/** An error that maps onto a JSON-RPC error object. */
class RpcError extends Error {
  constructor(code, message, data) {
    super(message);
    this.name = 'RpcError';
    this.code = code;
    if (data !== undefined) this.data = data;
  }

  toJSON() {
    const error = { code: this.code, message: this.message };
    if (this.data !== undefined) error.data = this.data;
    return error;
  }
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

/** A request id is valid when it is a string or an integer-valued number. */
function isValidId(id) {
  return typeof id === 'string' || (typeof id === 'number' && Number.isFinite(id));
}

function errorResponse(id, code, message, data) {
  const error = { code, message };
  if (data !== undefined) error.data = data;
  return { jsonrpc: '2.0', id: id === undefined ? null : id, error };
}

const TYPE_CHECKS = {
  string: (v) => typeof v === 'string',
  number: (v) => typeof v === 'number' && Number.isFinite(v),
  integer: (v) => Number.isInteger(v),
  boolean: (v) => typeof v === 'boolean',
  object: (v) => isPlainObject(v),
  array: (v) => Array.isArray(v),
  null: (v) => v === null
};

/**
 * Validate tool arguments against the top level of a JSON Schema object:
 * required members, primitive types and enums. Returns an error message, or
 * null when the arguments are acceptable. Unknown members are tolerated.
 */
function validateArguments(schema, args) {
  if (!isPlainObject(args)) return 'arguments must be an object';
  if (!schema || !isPlainObject(schema)) return null;
  for (const name of schema.required || []) {
    if (args[name] === undefined) return `missing required argument: ${name}`;
  }
  const properties = schema.properties || {};
  for (const [name, value] of Object.entries(args)) {
    const spec = properties[name];
    if (!spec || value === undefined) continue;
    if (spec.type) {
      const types = Array.isArray(spec.type) ? spec.type : [spec.type];
      if (!types.some((t) => (TYPE_CHECKS[t] || (() => true))(value))) {
        return `argument ${name} must be of type ${types.join(' or ')}`;
      }
    }
    if (Array.isArray(spec.enum) && !spec.enum.includes(value)) {
      return `argument ${name} must be one of: ${spec.enum.join(', ')}`;
    }
  }
  return null;
}

/**
 * Split a byte stream into newline-delimited frames. Handles frames split
 * across chunks, CRLF endings and multi-byte UTF-8 sequences split across
 * chunks. A frame longer than `maxBytes` is dropped (onOverflow is called once)
 * up to the next newline so a runaway writer cannot exhaust memory.
 */
function createLineDecoder(onLine, { maxBytes = 64 * 1024 * 1024, onOverflow = () => {} } = {}) {
  const decoder = new StringDecoder('utf8');
  let buffer = '';
  let discarding = false;

  function emit(line) {
    if (line.endsWith('\r')) line = line.slice(0, -1);
    onLine(line);
  }

  return {
    push(chunk) {
      buffer += typeof chunk === 'string' ? chunk : decoder.write(chunk);
      let index;
      while ((index = buffer.indexOf('\n')) !== -1) {
        const line = buffer.slice(0, index);
        buffer = buffer.slice(index + 1);
        if (discarding) { discarding = false; continue; }
        emit(line);
      }
      if (!discarding && Buffer.byteLength(buffer) > maxBytes) {
        discarding = true;
        buffer = '';
        onOverflow();
      } else if (discarding) {
        buffer = '';
      }
    },
    end() {
      buffer += decoder.end();
      if (!discarding && buffer.length) emit(buffer);
      buffer = '';
    }
  };
}

/** Run async tasks strictly one after another, in submission order. */
function createSerialQueue() {
  let tail = Promise.resolve();
  return function enqueue(task) {
    const run = tail.then(() => task());
    tail = run.catch(() => {});
    return run;
  };
}

module.exports = {
  RPC_ERRORS,
  RpcError,
  isPlainObject,
  isValidId,
  errorResponse,
  validateArguments,
  createLineDecoder,
  createSerialQueue
};
