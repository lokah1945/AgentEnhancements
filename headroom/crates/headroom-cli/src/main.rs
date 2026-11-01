use clap::{Parser, Subcommand};
use headroom_core::ccr::InMemoryCcrStore;
use headroom_core::transforms::pipeline::{
    CompressionPipeline, CompressionPipelineBuilder, PipelineConfig, PipelineMode, PipelineResult,
};
use headroom_core::transforms::pipeline::offloads::{
    DiffNoise, DiffOffload, JsonOffload, LogOffload, ProseFieldOffload,
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

impl From<CompressionMode> for PipelineMode {
    fn from(mode: CompressionMode) -> Self {
        match mode {
            CompressionMode::Auto => PipelineMode::Auto,
            CompressionMode::Code => PipelineMode::Code,
            CompressionMode::Logs => PipelineMode::Logs,
            CompressionMode::Json => PipelineMode::Json,
            CompressionMode::Markdown => PipelineMode::Markdown,
            CompressionMode::Generic => PipelineMode::Generic,
        }
    }
}

fn build_pipeline(mode: PipelineMode) -> CompressionPipeline {
    let config = PipelineConfig::default();
    let mut builder = CompressionPipeline::builder().with_config(config.clone());

    // Always add reformats
    builder = builder.with_reformat(JsonMinifier).with_reformat(LogTemplate::new(config.reformat.log_template));

    // Add offloads based on mode
    match mode {
        PipelineMode::Json => {
            builder = builder.with_offload(JsonOffload::from_pipeline(&config));
        }
        PipelineMode::Logs => {
            builder = builder
                .with_offload(LogOffload::new(config.bloat.log))
                .with_offload(ProseFieldOffload::new(config.offload.prose_field));
        }
        PipelineMode::Code => {
            builder = builder
                .with_offload(DiffOffload::new(config.bloat.diff))
                .with_offload(DiffNoise::new(config.offload.diff_noise));
        }
        PipelineMode::Markdown => {
            builder = builder.with_offload(ProseFieldOffload::new(config.offload.prose_field));
        }
        PipelineMode::Auto | PipelineMode::Generic => {
            // Use all transforms
            builder = builder
                .with_offload(JsonOffload::from_pipeline(&config))
                .with_offload(LogOffload::new(config.bloat.log))
                .with_offload(DiffOffload::new(config.bloat.diff))
                .with_offload(DiffNoise::new(config.offload.diff_noise))
                .with_offload(ProseFieldOffload::new(config.offload.prose_field));
        }
    }

    builder.build()
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
            PipelineMode::Json => ContentType::JsonArray,
            PipelineMode::Logs => ContentType::BuildOutput,
            PipelineMode::Code => ContentType::GitDiff,
            PipelineMode::Markdown => ContentType::PlainText,
            PipelineMode::Generic | PipelineMode::Auto => ContentType::PlainText,
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

            let pipeline = build_pipeline(mode.into());
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
        Commands::Mcp { transport } => {
            eprintln!("MCP server not yet implemented for CLI. Use headroom-proxy for proxy mode.");
            std::process::exit(1);
        }
    }

    Ok(())
}
