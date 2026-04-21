# Embedded / Firmware Domain Checklist

Questions for firmware, bare-metal, RTOS, and hardware-adjacent systems.

## Hardware Interface

1. **Target hardware?** "MCU family, SoC, or custom board? ARM Cortex-M is common for real-time. What are your memory (RAM/Flash) constraints?"
2. **Peripheral interfaces?** "UART, SPI, I2C, CAN, ADC, DAC, GPIO? List critical peripherals that must be supported."
3. **Real-time requirements?** "Hard real-time (deadline miss = failure), firm real-time (occasional miss acceptable), or soft real-time (best effort)? Worst-case interrupt latency budget?"
4. **Boot sequence?** "Single-stage, multi-stage with bootloader, or OTA-updatable? Boot time budget?"

## Software Architecture

5. **OS / runtime?** "Bare-metal super-loop, RTOS (FreeRTOS, Zephyr, ThreadX), or embedded Linux? Determines driver model, scheduling, and IPC."
6. **Programming language?** "C for maximum portability and tooling. C++ for abstraction. Rust for memory safety. What does your toolchain support?"
7. **Memory management?** "Static allocation only (safety-critical), heap with arena/pool allocators, or mixed? Stack size budget per task?"
8. **State machine design?** "Flat, hierarchical, or event-driven? How many concurrent states does the system need?"

## Safety & Reliability

9. **Safety standard?** "ISO 26262 (automotive), IEC 62304 (medical), IEC 61508 (industrial), DO-178C (aerospace), or none? This drives documentation and testing rigor."
10. **Watchdog strategy?** "Hardware watchdog, software watchdog, or both? Timeout periods? What constitutes a healthy heartbeat?"
11. **Error handling?** "Fail-safe defaults, redundant channels, or limp-home mode? How should the system behave when a peripheral fails?"
12. **Update mechanism?** "In-field firmware update needed? Dual-bank, A/B partition, or delta patching? Rollback strategy?"

## Communication

13. **Bus protocols?** "CAN, LIN, FlexRay, Ethernet? What protocols exist on the vehicle/network, and which need to be bridged?"
14. **Data logging?** "On-board storage, telemetry streaming, or both? What data must survive power loss?"
15. **Diagnostic interface?** "UDS/OBD-II, custom CLI, or debug port? What diagnostics must be available in production?"

## Testing & Verification

16. **Test hardware?** "Dev boards, production-representative prototypes, or hardware-in-the-loop (HIL) simulation? What's available for testing?"
17. **Code coverage target?** "MC/DC for safety-critical (ISO 26262 ASIL C/D), statement coverage for less critical. What level is required?"
18. **Static analysis?** "MISRA-C compliance, Polyspace, PC-lint, or clang static analyzer? Any mandated coding standard?"
