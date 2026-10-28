import Cocoa
import CoreGraphics
import Foundation

struct WindowInfo: Codable {
    let windowId: Int
    let ownerName: String
    let windowTitle: String
    let x: Double
    let y: Double
    let width: Double
    let height: Double
    let layer: Int
    let isOnScreen: Bool
}

func getOnScreenWindows() -> [WindowInfo] {
    var result: [WindowInfo] = []
    let options: CGWindowListOption = [.excludeDesktopElements]
    guard let windowListInfo = CGWindowListCopyWindowInfo(options, kCGNullWindowID) as? [[String: Any]] else {
        return result
    }

    for info in windowListInfo {
        let wid = info[kCGWindowNumber as String] as? Int ?? 0
        let owner = info[kCGWindowOwnerName as String] as? String ?? ""
        let title = info[kCGWindowName as String] as? String ?? ""
        let layer = info[kCGWindowLayer as String] as? Int ?? 0
        let boundsDict = info[kCGWindowBounds as String] as? [String: Any] ?? [:]

        let x = boundsDict["X"] as? Double ?? 0.0
        let y = boundsDict["Y"] as? Double ?? 0.0
        let w = boundsDict["Width"] as? Double ?? 0.0
        let h = boundsDict["Height"] as? Double ?? 0.0

        // Exclude system windows, tiny popups, and self-window
        if w >= 150 && h >= 150 && layer == 0 {
            if title.contains("Binh 13 Analyzer") {
                continue
            }
            result.append(WindowInfo(
                windowId: wid,
                ownerName: owner,
                windowTitle: title,
                x: x,
                y: y,
                width: w,
                height: h,
                layer: layer,
                isOnScreen: true
            ))
        }
    }
    return result
}

let windows = getOnScreenWindows()
let encoder = JSONEncoder()
encoder.outputFormatting = .prettyPrinted
if let data = try? encoder.encode(windows), let jsonStr = String(data: data, encoding: .utf8) {
    print(jsonStr)
} else {
    print("[]")
}
