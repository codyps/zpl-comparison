//! Adapter API sources and workload contracts: ../../../../README.md.
//! Build exactly one feature at a time to measure each dependency separately.
use std::{env, fs, hint::black_box, time::Instant};
mod probe;

#[cfg(feature = "codyps-zpl")]
fn render_options(width: u32, height: u32) -> codyps_zpl::Options {
    use codyps_zpl::render::profiles::{ZD621_203_DPI, ZQ610_PLUS_203_DPI};
    // Select the captured device explicitly; dimensions alone do not select
    // firmware behavior (in particular ZQ610 ^LL and preview width handling).
    let profile = match env::var("ZPL_RENDER_PROFILE").as_deref() {
        Ok("zq610-plus-203dpi") => ZQ610_PLUS_203_DPI,
        Ok("zd621-203dpi") | Err(env::VarError::NotPresent) => ZD621_203_DPI,
        other => panic!("unknown ZPL_RENDER_PROFILE: {other:?}"),
    };
    codyps_zpl::Options {
        width,
        height,
        dpi: 203,
        ..profile
    }
}

fn operation(mode: &str, input: &[u8], width: u32, height: u32) -> Vec<u8> {
    #[cfg(feature = "codyps-zpl")]
    {
        if mode == "parse" {
            let mut count = 0u64;
            for item in codyps_zpl::parse::ParseContext::from_bytes(black_box(input)) {
                black_box(item.expect("parse"));
                count += 1;
            }
            return count.to_le_bytes().to_vec();
        }
        use codyps_zpl::output::Adapter;
        let doc =
            codyps_zpl::render(black_box(input), render_options(width, height)).expect("render");
        assert_eq!(doc.labels.len(), 1);
        return codyps_zpl::output::Png.encode(&doc.labels[0]).expect("PNG");
    }
    #[cfg(feature = "toolchain")]
    {
        assert_eq!(mode, "parse");
        let parsed = toolchain::parse_str(black_box(std::str::from_utf8(input).unwrap()));
        assert!(!parsed.ast.labels.is_empty());
        let n = parsed.ast.labels.len() as u64;
        black_box(parsed);
        return n.to_le_bytes().to_vec();
    }
    #[cfg(feature = "labelize")]
    {
        let labels = labelize::ZplParser::new()
            .parse(black_box(input))
            .expect("parse");
        assert_eq!(labels.len(), 1);
        if mode == "parse" {
            let n = labels[0].elements.len() as u64;
            black_box(labels);
            return n.to_le_bytes().to_vec();
        }
        let mut png = Vec::new();
        labelize::Renderer::new()
            .draw_label_as_png(
                &labels[0],
                &mut png,
                labelize::DrawerOptions {
                    label_width_mm: width as f64 / 8.0,
                    label_height_mm: height as f64 / 8.0,
                    dpmm: 8,
                    ..Default::default()
                },
            )
            .expect("PNG");
        return png;
    }
    #[cfg(feature = "forge")]
    {
        let engine = forge::ZplEngine::new(
            black_box(std::str::from_utf8(input).unwrap()),
            forge::Unit::Dots(width),
            forge::Unit::Dots(height),
            forge::Resolution::Dpi203,
        )
        .expect("parse");
        if mode == "parse" {
            black_box(engine);
            return vec![1];
        }
        return engine.to_png().expect("PNG");
    }
    #[cfg(feature = "builder")]
    {
        assert_eq!(mode, "generate");
        let fields: u16 = std::str::from_utf8(input).unwrap().trim().parse().unwrap();
        let mut label = builder::LabelBuilder::new();
        for i in 0..fields {
            label = label
                .add_text(
                    &format!("Item {i:02}"),
                    10 + (i % 4) * 95,
                    10 + (i / 4) * 22,
                    'A',
                    16,
                    builder::Orientation::Normal,
                )
                .unwrap();
        }
        return label.build().into_bytes();
    }
    #[cfg(feature = "ffi")]
    {
        assert!(matches!(mode, "png" | "accuracy"));
        return ffi::render_bytes_with_options(
            black_box(input),
            &ffi::RenderOptions::new().size(width as i32, height as i32),
        )
        .expect("PNG");
    }
}

fn main() {
    let args: Vec<_> = env::args().collect();
    let input = fs::read(&args[2]).unwrap();
    let width = args.get(5).map(|s| s.parse().unwrap()).unwrap_or(400);
    let height = args.get(6).map(|s| s.parse().unwrap()).unwrap_or(300);
    if args[1].starts_with("probe-") {
        probe::run(&args[1], &input, &args[4], width, height);
        return;
    }
    if args[1] == "accuracy" {
        fs::write(&args[4], operation(&args[1], &input, width, height)).unwrap();
        return;
    }
    let n: u64 = args[3].parse().unwrap();
    assert!(n > 0);
    // Warm-up is outside the timer, but included in process peak RSS.
    let warmup = Instant::now();
    let mut warmed = 0;
    while warmed < 3 || (env::var("ZPL_BENCH_MEMORY").as_deref() != Ok("1") && warmup.elapsed().as_millis() < 250) {
        black_box(operation(&args[1], &input, width, height));
        warmed += 1;
    }
    let start = Instant::now();
    let mut checksum = 0u64;
    for _ in 0..n {
        let output = black_box(operation(&args[1], black_box(&input), width, height));
        checksum = checksum.wrapping_add(output.len() as u64);
        black_box(output);
    }
    let ns = start.elapsed().as_nanos();
    // Output capture is outside the timer; full output is consumed in the loop.
    fs::write(&args[4], operation(&args[1], &input, width, height)).unwrap();
    println!("{{\"ns\":{ns},\"iterations\":{n},\"checksum\":{checksum}}}");
}
