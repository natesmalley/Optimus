# 📱 Xcode Setup Instructions for Optimus iOS App

## Prerequisites
- ✅ Xcode 15.0 or later installed
- ✅ Apple Developer Account (free or paid)
- ✅ iOS 17.0+ device or simulator

## Step-by-Step Setup in Xcode

### 1. Open the Project
```bash
cd /Users/nathanial.smalley/projects/Optimus/iOS
open OptimusApp.xcodeproj
```

Or in Xcode:
- File → Open → Navigate to `/Users/nathanial.smalley/projects/Optimus/iOS/OptimusApp.xcodeproj`

### 2. Configure Your Development Team

1. **Select the project** in the navigator (blue icon at top)
2. **Select "Optimus" target**
3. Go to **"Signing & Capabilities"** tab
4. Check **"Automatically manage signing"**
5. Select your **Team** from dropdown:
   - If you have a paid account: Select your developer team
   - If using free account: Select "Personal Team"

### 3. Update Bundle Identifier

Change the bundle identifier to something unique:
1. In **"Signing & Capabilities"**
2. Change **Bundle Identifier** from `com.optimus.assistant` to:
   - Paid account: `com.yourcompany.optimus`
   - Free account: `com.yourname.optimus.assistant`

### 4. Configure API Endpoint

Since the app needs to connect to your local server:

#### Option A: Testing on Simulator
The current `localhost:8003` will work as-is.

#### Option B: Testing on Real Device
1. Get your Mac's IP address:
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
# Look for something like 192.168.1.100
```

2. Update `APIManager.swift`:
```swift
// Change from:
private var baseURL: String = "http://localhost:8003"
// To:
private var baseURL: String = "http://YOUR_MAC_IP:8003"
```

### 5. Add Required Capabilities

In Xcode, with your target selected:

1. Click **"+ Capability"** button
2. Add these capabilities:
   - **Background Modes**: Check `Audio`, `Background fetch`, `Background processing`
   - **Push Notifications** (if you have paid account)
   - **Siri** (for shortcuts)

### 6. Build and Run

#### On Simulator:
1. Select an iPhone simulator (e.g., "iPhone 15 Pro")
2. Press **Cmd+R** or click the **Play button** ▶️

#### On Real Device:
1. Connect your iPhone via USB
2. Select your device from the device menu
3. Trust the computer on your iPhone if prompted
4. Press **Cmd+R** or click the **Play button** ▶️

### 7. Trust Developer Certificate (First Run on Device)

If running on a real device with free account:
1. On iPhone: Settings → General → VPN & Device Management
2. Tap on your Developer App certificate
3. Tap "Trust [Your Apple ID]"
4. Launch the app again

## Current Project Structure

```
iOS/
├── OptimusApp.xcodeproj        # Xcode project file
├── OptimusApp/
│   ├── Info.plist              # App configuration
│   ├── Sources/
│   │   ├── OptimusApp.swift    # Main app entry
│   │   ├── Views/
│   │   │   └── ContentView.swift # UI components
│   │   └── Managers/
│   │       ├── APIManager.swift   # Backend communication
│   │       └── VoiceManager.swift # Voice & Speech
│   └── Assets.xcassets         # Icons and images
└── Package.swift               # Swift package dependencies
```

## Features Ready to Test

### ✅ Working Now
1. **Dashboard View** - Shows daily summary
2. **Voice Interface** - Tap to speak with Optimus
3. **Agenda View** - Today's events and tasks
4. **Quick Actions** - Add tasks, check calendar
5. **API Integration** - Connects to your backend

### 🔧 Needs Configuration
1. **Siri Shortcuts** - Requires Intents extension
2. **Widgets** - Requires Widget extension
3. **Apple Watch** - Requires Watch app target
4. **Push Notifications** - Requires certificates

## Common Issues & Solutions

### Issue: "Unable to install app"
**Solution**: Check bundle ID is unique and team is selected

### Issue: "Could not launch app"
**Solution**: Trust developer certificate on device (Settings → General → VPN & Device Management)

### Issue: "Network connection failed"
**Solution**: 
- For device: Use Mac's IP address instead of localhost
- Check server is running: `curl http://localhost:8003/api/health`

### Issue: "Microphone access denied"
**Solution**: Reset permissions in Settings → Privacy → Microphone

### Issue: "No matching provisioning profile"
**Solution**: 
1. Clean build folder (Cmd+Shift+K)
2. Delete derived data
3. Re-select team in Signing

## Next Steps After Setup

### 1. Test Core Features
- [ ] Launch app and verify dashboard loads
- [ ] Test voice commands
- [ ] Try quick add task
- [ ] Check if Council responses work

### 2. Customize for Production
- [ ] Replace localhost with production server URL
- [ ] Add app icons in Assets.xcassets
- [ ] Configure push notification certificates
- [ ] Set up TestFlight for beta testing

### 3. Add Extensions
- [ ] Widget Extension (for home screen widgets)
- [ ] Intents Extension (for Siri)
- [ ] Watch App (for Apple Watch)

## Testing Voice Commands

Once running, try these commands:
1. "Hey Optimus, what's my schedule?"
2. "Add task: Review pull requests"
3. "Should I take this meeting?"
4. "Plan my day"

## Build Settings Reference

| Setting | Debug | Release |
|---------|-------|---------|
| Base URL | http://localhost:8003 | https://your-server.com |
| Optimization | None | Whole Module |
| Debug Symbols | Yes | No |
| Code Signing | Development | Distribution |

## Deployment Checklist

Before submitting to App Store:
- [ ] Change API URL to production
- [ ] Add app icons (all sizes)
- [ ] Create screenshots for all device sizes
- [ ] Write App Store description
- [ ] Set up privacy policy URL
- [ ] Test on multiple devices
- [ ] Archive and upload to App Store Connect

## Resources

- [Apple Developer Documentation](https://developer.apple.com/documentation/)
- [SwiftUI Tutorials](https://developer.apple.com/tutorials/swiftui)
- [TestFlight](https://developer.apple.com/testflight/)
- [App Store Connect](https://appstoreconnect.apple.com)

---

## Quick Commands

### Build & Run
```bash
# Command line build (requires xcrun)
xcodebuild -project OptimusApp.xcodeproj -scheme Optimus -destination 'platform=iOS Simulator,name=iPhone 15 Pro'

# Open in Xcode
open OptimusApp.xcodeproj
```

### Clean & Reset
```bash
# Clean build
xcodebuild clean

# Delete derived data
rm -rf ~/Library/Developer/Xcode/DerivedData/OptimusApp-*
```

---

**Ready to transform and roll out on iOS!** 🚀📱

If Xcode is open, you should now:
1. Select your development team
2. Choose a simulator or connect your device
3. Press the Play button to build and run!

The app will connect to your local Optimus server at `http://localhost:8003`.