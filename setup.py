from setuptools import setup

setup(
    app=["main.py"],
    options={
        "py2app": {
            "argv_emulation": False,
            "plist": {
                "CFBundleName": "VimMouse",
                "CFBundleIdentifier": "com.vimmouse.app",
                "CFBundleVersion": "0.1.0",
                "CFBundleShortVersionString": "0.1.0",
                "LSUIElement": True,
                "NSAccessibilityUsageDescription": "VimMouse needs Accessibility access to detect UI elements and simulate clicks.",
            },
            "packages": [
                "objc",
                "AppKit",
                "Foundation",
                "Quartz",
                "CoreFoundation",
                "CoreText",
                "ApplicationServices",
                "HIServices",
                "PyObjCTools",
            ],
        }
    },
    setup_requires=["py2app"],
)
