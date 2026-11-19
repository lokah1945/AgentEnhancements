// AgentEnhancements modification, 2026-11-19: repair CLI modes and keep
// standalone output self-contained without process-local CCR offloads.
use clap::{Parser, Subcommand};
use headroom_core::ccr::InMemoryCcrStore;
use headroom_core::transforms::pipeline::{
    CompressionPipeline, PipelineConfig, PipelineResult,
};
use headroom_core::transforms::pipeline::reformats::{JsonMinifier, LogTemplate};
use headroom_core::transforms::pipeline::traits::CompressionContext;
use headroom_core::transforms::ContentType;
use std::io::{self, Read};

#[derive(Parser)]
#[command(name = "headroom", about = "Headroom context compression CLI", version)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Compress content from stdin or file
    Compress {
        /// Compression mode
        #[arg(short, long, default_value = "auto")]
        mode: CompressionMode,

        /// Input file (stdin if not provided)
        #[arg(short, long)]
        input: Option<String>,

        /// Output file (stdout if not provided)
        #[arg(short, long)]
        output: Option<String>,
    },
    /// Start MCP server
    Mcp {
        /// Listen address
        #[arg(long, default_value = "stdio")]
        transport: String,
    },
}

#[derive(clap::ValueEnum, Clone, Copy, Debug, PartialEq)]
enum CompressionMode {
    Auto,
    Code,
    Logs,
    Json,
    Markdown,
    Generic,
}


fn build_pipeline(_mode: CompressionMode) -> CompressionPipeline {
    let config = PipelineConfig::default();
    // The standalone process has no retrieval service after it exits.
    // Only use self-contained reformats; CCR offloads belong to long-lived
    // hosts that retain their store and expose a retrieval tool.
    CompressionPipeline::builder()
        .with_config(config.clone())
        .with_reformat(JsonMinifier)
        .with_reformat(LogTemplate::new(config.reformat.log_template))
        .build()
}

fn detect_content_type(content: &str, mode: CompressionMode) -> ContentType {
    if mode == CompressionMode::Auto {
        // Simple detection
        if content.trim().starts_with('{') || content.trim().starts_with('[') {
            ContentType::JsonArray
        } else if content.lines().any(|l| l.contains("ERROR") || l.contains("WARN") || l.contains("INFO") || l.contains("DEBUG")) {
            ContentType::BuildOutput
        } else if content.contains("diff --git") || content.contains("@@") {
            ContentType::GitDiff
        } else {
            ContentType::PlainText
        }
    } else {
        match mode {
            CompressionMode::Json => ContentType::JsonArray,
            CompressionMode::Logs => ContentType::BuildOutput,
            CompressionMode::Code => ContentType::GitDiff,
            CompressionMode::Markdown => ContentType::PlainText,
            CompressionMode::Generic | CompressionMode::Auto => ContentType::PlainText,
        }
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Compress { mode, input, output } => {
            let content = if let Some(path) = input {
                std::fs::read_to_string(path)?
            } else {
                let mut buf = String::new();
                io::stdin().read_to_string(&mut buf)?;
                buf
            };

            let pipeline = build_pipeline(mode);
            let content_type = detect_content_type(&content, mode);
            let ctx = CompressionContext::default();
            let store = InMemoryCcrStore::new();

            let result: PipelineResult = pipeline.run(&content, content_type, &ctx, &store);

            if let Some(path) = output {
                std::fs::write(path, &result.output)?;
            } else {
                println!("{}", result.output);
            }

            // Print stats to stderr
            eprintln!("Compression: {} -> {} bytes ({} bytes saved, {} steps)",
                content.len(), result.output.len(), result.bytes_saved, result.steps_applied.len());
        }
        Commands::Mcp { transport: _ } => {
            eprintln!("MCP server not yet implemented for CLI. Use headroom-proxy for proxy mode.");
            std::process::exit(1);
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn explicit_modes_detect_the_expected_content_types() {
        for (mode, expected) in [
            (CompressionMode::Code, ContentType::GitDiff),
            (CompressionMode::Logs, ContentType::BuildOutput),
            (CompressionMode::Json, ContentType::JsonArray),
            (CompressionMode::Markdown, ContentType::PlainText),
            (CompressionMode::Generic, ContentType::PlainText),
        ] {
            assert_eq!(detect_content_type("example", mode), expected);
        }
    }

    #[test]
    fn json_mode_preserves_values() {
        let input = "{\"keep\":null,\"empty\":\"\",\"values\":[1,2,3]}";
        let result = build_pipeline(CompressionMode::Json).run(
            input, ContentType::JsonArray, &CompressionContext::default(),
            &InMemoryCcrStore::new(),
        );
        assert_eq!(serde_json::from_str::<serde_json::Value>(&result.output).unwrap(),
                   serde_json::from_str::<serde_json::Value>(input).unwrap());
    }

    #[test]
    fn standalone_json_keeps_every_row_without_transient_offloads() {
        let rows: Vec<_> = (0..1000).map(|i| serde_json::json!({
            "id": i, "status": "pending", "description": "repetitive fixture record"
        })).collect();
        let input = serde_json::to_string(&rows).unwrap();
        let result = build_pipeline(CompressionMode::Json).run(
            &input, ContentType::JsonArray, &CompressionContext::default(),
            &InMemoryCcrStore::new(),
        );
        assert!(result.cache_keys.is_empty(), "CLI cannot retrieve cache entries after exit");
        assert_eq!(serde_json::from_str::<serde_json::Value>(&result.output).unwrap(),
                   serde_json::from_str::<serde_json::Value>(&input).unwrap());
    }
}
