// codyps/zpl Go API with its default wasm2go backend; source pinned in sources.lock.json.
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"runtime"
	"strconv"
	"time"

	zpl "github.com/codyps/zpl/zpl-go"
)

func operation(mode string, input []byte, width, height int) ([]byte, error) {
	if mode == "parse" || mode == "probe-parse" {
		return nil, fmt.Errorf("adapter does not expose parsing")
	}
	profile := zpl.ZD621
	switch value := os.Getenv("ZPL_RENDER_PROFILE"); value {
	case "", "zd621-203dpi", "zd621-preview-203dpi":
	case "zq610-plus-203dpi":
		profile = zpl.ZQ610Plus
	default:
		return nil, fmt.Errorf("unknown ZPL_RENDER_PROFILE: %s", value)
	}
	ctx := context.Background()
	engine, err := zpl.New(ctx)
	if err != nil {
		return nil, err
	}
	defer engine.Close(ctx)
	result, err := engine.Render(ctx, zpl.Request{
		Input: input, Format: zpl.PNG, Profile: profile,
		Width: uint32(width), Height: uint32(height),
	})
	if err != nil {
		return nil, err
	}
	if result.Labels != 1 {
		return nil, fmt.Errorf("expected one label, got %d", result.Labels)
	}
	return result.Body, nil
}

func positive(value string) int {
	n, err := strconv.Atoi(value)
	if err != nil || n < 1 {
		panic("expected positive integer")
	}
	return n
}

func main() {
	mode, file, output := os.Args[1], os.Args[2], os.Args[4]
	input, err := os.ReadFile(file)
	if err != nil {
		panic(err)
	}
	n := positive(os.Args[3])
	width, height := 400, 300
	if len(os.Args) > 6 {
		width, height = positive(os.Args[5]), positive(os.Args[6])
	}
	if mode == "probe-parse" || mode == "probe-render" {
		out, err := operation(mode, input, width, height)
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			fmt.Println("rejected")
		} else if len(out) == 0 {
			fmt.Println("accepted-empty")
		} else {
			if mode == "probe-render" {
				if err := os.WriteFile(output, out, 0644); err != nil {
					panic(err)
				}
			}
			fmt.Println("accepted")
		}
		return
	}
	call := func() []byte {
		out, err := operation(mode, input, width, height)
		if err != nil {
			panic(err)
		}
		if len(out) == 0 {
			panic("renderer returned no labels")
		}
		return out
	}
	if mode != "accuracy" {
		warmup := time.Now()
		for i := 0; i < 3 || (os.Getenv("ZPL_BENCH_MEMORY") != "1" && time.Since(warmup) < 250*time.Millisecond); i++ {
			runtime.KeepAlive(call())
		}
		start, checksum := time.Now(), 0
		for i := 0; i < n; i++ {
			out := call()
			checksum += len(out)
			runtime.KeepAlive(out)
		}
		elapsed := time.Since(start).Nanoseconds()
		if err := json.NewEncoder(os.Stdout).Encode(map[string]any{"ns": elapsed, "iterations": n, "checksum": checksum}); err != nil {
			panic(err)
		}
	}
	if err := os.WriteFile(output, call(), 0644); err != nil {
		panic(err)
	}
}
