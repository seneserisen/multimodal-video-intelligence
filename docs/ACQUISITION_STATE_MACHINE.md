# Acquisition state machine

1. Validate URL and identify platform.
2. Attempt supported official/direct provider access.
3. Attempt best-effort direct local extraction.
4. Detect whether media plays in the active browser tab.
5. Capture the authenticated browser tab.
6. Fall back to explicitly selected window/screen capture.
7. Validate audio and video.
8. Return structured terminal diagnostics after applicable paths are exhausted.

Every attempt records method, outcome, and a safe diagnostic. The system never bypasses DRM, paywalls, private permissions, CAPTCHA, geography, or other access controls. Cookie export is not a default path. This state machine is designed, not implemented, in Milestone 1.
