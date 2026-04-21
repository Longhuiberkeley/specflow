# Mobile Application Domain Checklist

Questions for iOS, Android, and cross-platform mobile applications.

## Platform & Architecture

1. **Target platforms?** "iOS only, Android only, or both? Cross-platform (React Native, Flutter, KMP) reduces duplication but limits native API access. What's your team's expertise?"
2. **Minimum OS version?** "iOS 15+ and Android 10+ cover 95%+ of active devices. Going lower increases testing surface. What's your user demographic?"
3. **Architecture pattern?** "MVVM is standard for both platforms. MVI for unidirectional data flow. VIPER for large teams. Which fits your complexity?"
4. **Offline capability?** "Full offline, read-only offline, or online-only? Offline-first significantly increases complexity (sync, conflict resolution, local storage)."

## User Experience

5. **Screen complexity?** "Under 10 screens (utility app), 10-30 (standard), or 30+ (enterprise)? Determines navigation architecture."
6. **Accessibility?** "WCAG 2.1 AA compliance required? VoiceOver/TalkBack support? This affects every screen's layout and labeling."
7. **Internationalization?** "Single language, or multi-locale? RTL languages (Arabic, Hebrew) affect layout. What locales at launch?"
8. **Responsive targets?** "Phone only, or phone + tablet? Foldable devices? How should layouts adapt?"

## Data & Networking

9. **Backend API?** "REST, GraphQL, or Firebase/Supabase BaaS? Does the backend already exist, or is it being built in parallel?"
10. **Authentication?** "Biometric (Face ID / fingerprint), OAuth 2.0, magic link, or anonymous? Account recovery flow needed?"
11. **Push notifications?** "Transactional, marketing, or both? How critical is real-time delivery? What's the expected notification volume?"
12. **Local storage?** "Keychain/Keystore for secrets, UserDefaults/SharedPreferences for settings, SQLite/Realm for structured data. What needs to persist locally?"

## Performance & Reliability

13. **Startup time budget?** "Under 2 seconds is expected. Cold start vs warm start. What's acceptable?"
14. **Network conditions?** "3G fallback, intermittent connectivity, or always-on WiFi? How should the app behave on poor connections?"
15. **Battery impact?** "Background processing, GPS tracking, or BLE? High-drain features need careful lifecycle management."
16. **Crash rate target?** "Under 0.1% for consumer apps, under 0.01% for enterprise. Crash reporting solution (Crashlytics, Sentry)?"

## Distribution & Lifecycle

17. **App store review?** "Apple App Store review takes 24-48h typically. Any content that might trigger rejection (payments, user-generated content, health data)?"
18. **Update cadence?** "Weekly, biweekly, or monthly? Force-update mechanism needed for breaking changes?"
19. **Analytics & experimentation?** "Event tracking, A/B testing, or neither? Privacy regulations (GDPR, CCPA) affect what you can collect."
