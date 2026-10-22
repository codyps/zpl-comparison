//! Adapter API sources and workload contracts: ../../../../README.md.
//! Build exactly one feature at a time to measure each dependency separately.
use std::{env, fs, hint::black_box, time::Instant};
mod probe;

// The GX430t campaign uses the printer's marketed 300 DPI (12 dots/mm).
fn dpi() -> u32 {
    if env::var("ZPL_RENDER_PROFILE").as_deref() == Ok("gx430t-300dpi") {
        300
    } else {
        203
    }
}

#[cfg(feature = "codyps-zpl")]
fn render_options(width: u32, height: u32) -> codyps_zpl::Options {
    use codyps_zpl::render::profiles::{GX430T_300_DPI, ZD621_203_DPI, ZQ610_PLUS_203_DPI};
    // Select the captured device explicitly; dimensions alone do not select
    // firmware behavior (in particular ZQ610 ^LL and preview width handling).
    let profile = match env::var("ZPL_RENDER_PROFILE").as_deref() {
        Ok("zq610-plus-203dpi") => ZQ610_PLUS_203_DPI,
        Ok("gx430t-300dpi") => GX430T_300_DPI,
        Ok("zd621-preview-203dpi") => {
            let mut preview = ZD621_203_DPI;
            preview.compatibility.preview_width_quantum = Some(64);
            preview.compatibility.preview_width_latched_at_first_draw = true;
            preview
        }
        Ok("zd621-203dpi") | Err(env::VarError::NotPresent) => ZD621_203_DPI,
        other => panic!("unknown ZPL_RENDER_PROFILE: {other:?}"),
    };
    codyps_zpl::Options {
        width,
        height,
        dpi: dpi(),
        ..profile
    }
}

#[cfg(feature = "codyps-zpl")]
fn render_codyps(
    input: &[u8],
    width: u32,
    height: u32,
) -> Result<codyps_zpl::render::Document, String> {
    let options = render_options(width, height);
    let directory = env::var("ZPL_FONT_DIR").unwrap_or_default();
    if directory.is_empty() {
        return codyps_zpl::render(input, options).map_err(|e| format!("{e:?}"));
    }
    use codyps_zpl::{fonts::Fonts, truetype::Hinting};
    let read = |name: &str| {
        fs::read(std::path::Path::new(&directory).join(name))
            .map_err(|e| format!("controlled font {name}: {e}"))
    };
    let font0 = read("0.ttf")?;
    let swiss = read("Swiss.ttf")?;
    let mut fonts = Fonts::new();
    fonts.insert_truetype('0', &font0, Hinting::Native)?;
    fonts.insert_named_truetype("R:FC0.TTF", &font0, Hinting::Native)?;
    for device in ["R", "E", "B", "A"] {
        fonts.insert_named_truetype(&format!("{device}:TT0003M_.TTF"), &swiss, Hinting::Native)?;
    }
    // Recovered bitmap faces arrive through the shared ~DB/^CW preamble.
    codyps_zpl::render::render_with_fonts(input, options, &fonts).map_err(|e| format!("{e:?}"))
}

// Reusable public font setup, separate from ZplEngine::new's per-input parsing.
// https://docs.rs/zpl-forge/0.3.2/zpl_forge/struct.ZplEngine.html#method.set_fonts
#[cfg(feature = "forge")]
fn forge_fonts() -> std::sync::Arc<forge::FontManager> {
    static FONTS: std::sync::OnceLock<std::sync::Arc<forge::FontManager>> =
        std::sync::OnceLock::new();
    FONTS
        .get_or_init(|| {
            let mut fonts = forge::FontManager::default();
            if let Ok(directory) = env::var("ZPL_FONT_DIR") {
                if !directory.is_empty() {
                    for id in "0ABCDEFGHPQRSTUV".chars() {
                        let file = if id == 'C' { 'D' } else { id };
                        let bytes =
                            fs::read(std::path::Path::new(&directory).join(format!("{file}.ttf")))
                                .expect("supplied font");
                        fonts
                            .register_font(&format!("Comparison-{id}"), &bytes, id, id)
                            .expect("font registration");
                    }
                }
            }
            std::sync::Arc::new(fonts)
        })
        .clone()
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
        let doc = render_codyps(black_box(input), width, height).expect("render");
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
                    label_width_mm: width as f64 / (if dpi() == 300 { 12.0 } else { 8.0 }),
                    label_height_mm: height as f64 / (if dpi() == 300 { 12.0 } else { 8.0 }),
                    dpmm: if dpi() == 300 { 12 } else { 8 },
                    ..Default::default()
                },
            )
            .expect("PNG");
        return png;
    }
    #[cfg(feature = "forge")]
    {
        let mut engine = forge::ZplEngine::new(
            black_box(std::str::from_utf8(input).unwrap()),
            forge::Unit::Dots(width),
            forge::Unit::Dots(height),
            if dpi() == 300 {
                forge::Resolution::Dpi300
            } else {
                forge::Resolution::Dpi203
            },
        )
        .expect("parse");
        if mode == "parse" {
            black_box(engine);
            return vec![1];
        }
        engine.set_fonts(forge_fonts());
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
            &ffi::RenderOptions::new()
                .dpi(if dpi() == 300 {
                    ffi::Dpi::Dpi300
                } else {
                    ffi::Dpi::Dpi203
                })
                .size(width as i32, height as i32),
        )
        .expect("PNG");
    }
}

fn main() {
    let args: Vec<_> = env::args().collect();
    #[cfg(feature = "forge")]
    if args[1] == "init" {
        assert_eq!(args[3], "1", "one setup per fresh process");
        let start = Instant::now();
        let fonts = forge_fonts();
        let ns = start.elapsed().as_nanos();
        black_box(fonts);
        println!("{{\"ns\":{ns},\"iterations\":1,\"checksum\":1}}");
        return;
    }
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
    #[cfg(feature = "forge")]
    if args[1] != "parse" {
        // The fresh-process init lane measures this setup independently.
        black_box(forge_fonts());
    }
    let n: u64 = args[3].parse().unwrap();
    assert!(n > 0);
    // Warm-up is outside the timer, but included in process peak RSS.
    let warmup = Instant::now();
    let mut warmed = 0;
    while warmed < 3
        || (env::var("ZPL_BENCH_MEMORY").as_deref() != Ok("1")
            && warmup.elapsed().as_millis() < 250)
    {
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
