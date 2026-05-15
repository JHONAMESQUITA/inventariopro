[app]

# (str) Title of your application
title = Inventario PRO

# (str) Package name
package.name = inventariopro

# (str) Package domain (needed for android/ios packaging)
package.domain = org.inventariopro

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,ttf,txt,json,spec

# (list) List of inclusions using pattern matching
# source.include_patterns = assets/sounds/*.mp3, data/*.json

# (list) Source files to exclude (let empty to not exclude anything)
# source.exclude_dirs = tests, bin

# (list) List of directory to exclude from the APK
# source.exclude_dirs = .git, __pycache__, tests

# (list) List of patterns to exclude from the APK
# source.exclude_patterns = .gitignore, *.pyc

# (str) Application versioning (method 1)
version = 3.0.0

# (str) Application versioning (method 2)
# version.regex = __version__ = ['\"](.*)['\"]
# version.filename = %(source.dir)s/main.py

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3==3.13.3,kivy==2.3.0,openpyxl,requests,python-dotenv,Pillow,fpdf2,imaplib2

# (str) Custom source folders for requirements
# requirements.source.kivy = ./kivy

# (str) Presplash of the application
presplash.filename = icons/splash.png

# (str) Icon of the application
icon.filename = icons/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) List of service to declare
# services = NAME:ENTRYPOINT_TO_PY,NAME2:ENTRYPOINT2_TO_PY

# OSX / iOS
# ios_pods_name = kivy-ios

# (str) target android API, should be as high as possible.
android.api = 34

# (int) Android SDK version to use
android.sdk = 34

# (str) Android NDK version to use
# android.ndk = 25.1.8937393

# (bool) Use Android Studio build tools
android.gradle_dependencies = 'com.android.support:support-annotations:28.0.0'
android.accept_sdk_license = True

# (str) Android private storage path
# android.private_storage = .

# (list) Android permissions
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# (bool) Android x86 support
android.archs = arm64-v8a, armeabi-v7a

# (str) Python for Android branch (default is master)
# android.p4a_dir =

# (str) Android manifest theme
# android.theme = @android:style/Theme.DeviceDefault

# (list) Android extra libraries to add to the APK
# android.add_src =

# (str) Android logcat filter filter
# android.log_filter =

# (bool) Android copy library instead of making a libs directory
# android.copy_libs = 1

# (str) Android additional maven repository
# android.maven_repositories = https://jitpack.io

# (bool) Enable AndroidX
android.enable_androidx = True

# (bool) Use Google Play Services
# android.google_play_services = False

# (bool) Use Google Support Annotations
# android.use_support_library = True

# (list) The Android arch to build for.
# android.arch =

# (list) Gstreamer supported audio decoders
# android.gstreamer =

# (bool) Adds iOS support
# ios.supported = True

# (str) CocoaPods dependencies
# ios.cocoapods_deps = {ios.pods_name}

# (str) Local iOS app signing identity
# ios.provision_profile = YourProfile.mobileprovision

# (str) iOS entitlements file
# ios.entitlements =

# (bool) enable iOS project auto layout
# ios.automatically_manage_signing = False

# (str) Path to iOS Xcode project folder
# ios.xcode_project_dir =

# (int) Target iOS version
# ios.ios_version = 13.0

# (str) iOS bundle identifier
# ios.bundle_identifier = org.inventariopro.app

# (bool) If True, then the iOS project is built with bitcode support
# ios.bitcode = False

# (str) Path to the iOS signing certificate
# ios.codesign_certificate =

# (str) Path to the iOS provisioning profile
# ios.provision_profile =

# (str) iOS Simulator
# ios.simulator =

# (str) The path to the iOS project file
# ios.project_file =

# (str) The path to the iOS project file
# ios.xcodeproj =

# (str) The path to main.m
# ios.main_m =

# (str) The path to AppDelegate.m
# ios.app_delegate_m =

# (str) The path to Info.plist
# ios.info_plist =

# (str) The path to LaunchScreen.storyboard
# ios.launch_screen_storyboard =

# (str) The path to LaunchScreen.xib
# ios.launch_screen_xib =

# (list) iOS frameworks to link against
# ios.frameworks =

# (list) iOS weak frameworks to link against
# ios.weak_frameworks =

# (bool) Enable iOS ARC
# ios.arc =

# (str) iOS compiler flags
# ios.cflags =

# (str) iOS linker flags
# ios.ldflags =

# (str) iOS precompiled header
# ios.pch =

# (str) iOS entitlements
# ios.entitlements =

# (str) iOS project file path
# ios.xcodeproj =

# (bool) Enable iOS code signing
# ios.codesign =
