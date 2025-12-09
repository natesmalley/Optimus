// swift-tools-version: 5.9
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "OptimusApp",
    platforms: [
        .iOS(.v17),
        .watchOS(.v10),
        .macOS(.v14)
    ],
    products: [
        .library(
            name: "OptimusApp",
            targets: ["OptimusApp"]),
    ],
    dependencies: [
        // Networking
        .package(url: "https://github.com/Alamofire/Alamofire.git", from: "5.8.0"),
        // WebSocket
        .package(url: "https://github.com/socketio/socket.io-client-swift.git", from: "16.0.0"),
        // Keychain
        .package(url: "https://github.com/kishikawakatsumi/KeychainAccess.git", from: "4.2.0"),
    ],
    targets: [
        .target(
            name: "OptimusApp",
            dependencies: [
                "Alamofire",
                .product(name: "SocketIO", package: "socket.io-client-swift"),
                "KeychainAccess"
            ]),
        .testTarget(
            name: "OptimusAppTests",
            dependencies: ["OptimusApp"]),
    ]
)