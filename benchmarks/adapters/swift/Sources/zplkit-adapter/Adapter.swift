import Foundation
import ZPLKitRenderer

@main
struct Adapter {
    static func main() {
        do {
            try render()
        } catch {
            FileHandle.standardError.write(Data("\(error)\n".utf8))
            exit(1)
        }
    }

    static func render() throws {
        let args = Array(CommandLine.arguments.dropFirst())
        guard args.count == 6, args[0] == "accuracy", args[2] == "1",
              let width = Int(args[4]), width > 0,
              let height = Int(args[5]), height > 0 else {
            throw AdapterError.arguments
        }
        let bytes = try Data(contentsOf: URL(fileURLWithPath: args[1]))
        guard let source = String(data: bytes, encoding: .utf8) else {
            throw AdapterError.invalidUTF8
        }
        // The public API derives its canvas from ZPL. Preserve the exact source
        // and native result; the comparison records any dimension mismatch.
        let result = try ZPLRenderer().renderToPNG(source)
        try result.data.write(to: URL(fileURLWithPath: args[3]))
    }

    enum AdapterError: Error {
        case arguments
        case invalidUTF8
    }
}
