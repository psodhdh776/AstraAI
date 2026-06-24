"""
Build guide for Astra AI APK (Android).
Uses Chaquopy (Python embedded in Android Studio) or Kivy + Buildozer.

Option A: Chaquopy (Recommended) — embed Python in native Android app
1. Install Android Studio
2. Create new project, add Chaquipy plugin in build.gradle:
   plugins {
       id 'com.chaquo.python' version '15.0.1' apply false
   }
3. In app/build.gradle:
   python {
       buildPython "python3"
       pip {
           install "PySide6"
       }
   }
4. Copy modules/ to src/main/python/
5. Call Python from Kotlin:
   Python.getInstance().getModule("app").callAttr("main")

Option B: Kivy + Buildozer (Cross-platform GUI)
1. pip install kivy buildozer
2. Create buildozer.spec:
   title = Astra AI
   package.name = astraai
   package.domain = org.astraai
   source.dir = .
   requirements = python3,kivy,pyjnius,android
3. buildozer android debug deploy run

Option C: Termux (Run on-device without build)
1. Install Termux from F-Droid
2. pkg install python
3. pip install PySide6
4. python app.py

See: https://chaquo.com/chaquopy/ | https://buildozer.readthedocs.io/
"""
