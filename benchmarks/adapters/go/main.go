// API: https://github.com/StirlingMarketingGroup/go-zpl (pinned in sources.lock.json).
package main

import (
	"bytes"
	"fmt"
	zpl "github.com/StirlingMarketingGroup/go-zpl"
	"github.com/StirlingMarketingGroup/go-zpl/render"
	"os"
	"runtime"
	"strconv"
	"time"
)

func operation(mode, input string, width, height int) []byte {
	label, err := zpl.Parse(input)
	if err != nil {
		panic(err)
	}
	if mode == "parse" {
		runtime.KeepAlive(label)
		return []byte{1}
	}
	var out bytes.Buffer
	if err := render.New(zpl.DPI203).WithSize(width, height).RenderPNG(label, &out); err != nil {
		panic(err)
	}
	return out.Bytes()
}
func main() {
	input, err := os.ReadFile(os.Args[2])
	if err != nil {
		panic(err)
	}
	source := string(input)
	width, height := 400, 300
	if len(os.Args) > 6 {
		width, err = strconv.Atoi(os.Args[5])
		if err != nil {
			panic(err)
		}
		height, err = strconv.Atoi(os.Args[6])
		if err != nil {
			panic(err)
		}
	}
	if os.Args[1] == "accuracy" {
		if err := os.WriteFile(os.Args[4], operation(os.Args[1], source, width, height), 0644); err != nil {
			panic(err)
		}
		return
	}
	n, err := strconv.Atoi(os.Args[3])
	if err != nil || n < 1 {
		panic("iterations")
	}
	warmup := time.Now()
	for i := 0; i < 3 || time.Since(warmup) < 250*time.Millisecond; i++ {
		runtime.KeepAlive(operation(os.Args[1], source, width, height))
	}
	start := time.Now()
	checksum := 0
	for i := 0; i < n; i++ {
		out := operation(os.Args[1], source, width, height)
		checksum += len(out)
		runtime.KeepAlive(out)
	}
	ns := time.Since(start).Nanoseconds()
	if err := os.WriteFile(os.Args[4], operation(os.Args[1], source, width, height), 0644); err != nil {
		panic(err)
	}
	fmt.Printf("{\"ns\":%d,\"iterations\":%d,\"checksum\":%d}\n", ns, n, checksum)
}
