//! One-shot error probes: returned library errors are distinct from panics.
use std::fs;
#[cfg(any(
    feature = "codyps-zpl",
    feature = "toolchain",
    feature = "labelize",
    feature = "forge"
))]
use std::hint::black_box;

pub fn run(mode: &str, input: &[u8], output: &str, width: u32, height: u32) {
    match operation(mode, input, width, height) {
        Ok(bytes) => {
            if mode == "probe-render" && bytes.is_empty() {
                println!("accepted-empty");
            } else {
                if mode == "probe-render" {
                    fs::write(output, bytes).expect("write probe output");
                }
                println!("accepted");
            }
        }
        Err(error) => {
            eprintln!("{error}");
            println!("rejected");
        }
    }
}

fn operation(mode: &str, input: &[u8], width: u32, height: u32) -> Result<Vec<u8>, String> {
    #[cfg(feature = "codyps-zpl")]
    {
        if mode == "probe-parse" {
            for item in codyps_zpl::parse::ParseContext::from_bytes(input) {
                black_box(item.map_err(|e| format!("{e:?}"))?);
            }
            return Ok(vec![]);
        }
        use codyps_zpl::output::Adapter;
        let doc = super::render_codyps(input, width, height).map_err(|e| format!("{e:?}"))?;
        return match doc.labels.first() {
            Some(label) => codyps_zpl::output::Png
                .encode(label)
                .map_err(|e| format!("{e:?}")),
            None => Ok(vec![]),
        };
    }
    #[cfg(feature = "toolchain")]
    {
        let _ = (mode, width, height);
        let result = toolchain::parse_str(std::str::from_utf8(input).map_err(|e| e.to_string())?);
        for diagnostic in &result.diagnostics {
            eprintln!("{diagnostic:?}");
        }
        if result
            .diagnostics
            .iter()
            .any(|d| matches!(d.severity, toolchain::Severity::Error))
        {
            return Err("Parser returned error diagnostics".into());
        }
        black_box(result);
        return Ok(vec![]);
    }
    #[cfg(feature = "labelize")]
    {
        let labels = labelize::ZplParser::new()
            .parse(input)
            .map_err(|e| format!("{e:?}"))?;
        if mode == "probe-parse" {
            black_box(labels);
            return Ok(vec![]);
        }
        let Some(label) = labels.first() else {
            return Ok(vec![]);
        };
        let mut png = Vec::new();
        labelize::Renderer::new()
            .draw_label_as_png(
                label,
                &mut png,
                labelize::DrawerOptions {
                    label_width_mm: width as f64 / 8.0,
                    label_height_mm: height as f64 / 8.0,
                    dpmm: 8,
                    ..Default::default()
                },
            )
            .map_err(|e| format!("{e:?}"))?;
        return Ok(png);
    }
    #[cfg(feature = "forge")]
    {
        let engine = forge::ZplEngine::new(
            std::str::from_utf8(input).map_err(|e| e.to_string())?,
            forge::Unit::Dots(width),
            forge::Unit::Dots(height),
            forge::Resolution::Dpi203,
        )
        .map_err(|e| format!("{e:?}"))?;
        if mode == "probe-parse" {
            black_box(engine);
            return Ok(vec![]);
        }
        return engine.to_png().map_err(|e| format!("{e:?}"));
    }
    #[cfg(feature = "ffi")]
    {
        let _ = mode;
        return ffi::render_bytes_with_options(
            input,
            &ffi::RenderOptions::new().size(width as i32, height as i32),
        )
        .map_err(|e| format!("{e:?}"));
    }
    #[cfg(feature = "builder")]
    {
        let _ = (mode, input, width, height);
        unreachable!("Builder has no incoming-ZPL API")
    }
}
