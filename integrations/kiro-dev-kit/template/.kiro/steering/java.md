---
inclusion: fileMatch
fileMatchPattern: ["**/*.java","**/pom.xml","**/build.gradle*"]
---
Inspect the Maven/Gradle wrapper and declared Java release/toolchain. Prefer the repository wrapper and configured language level. Run targeted tests, then the required build. The kit's dependency-free fixture compiles with javac and runs explicit checks on JDK 27; that does not imply an existing project should be migrated to Java 27.
