# Library / SDK Domain Checklist

Questions for reusable packages, SDKs, and shared libraries.

## Interface

1. **Target language(s)?** "Single language or multi-language (via bindings, transpilation, or protocol)? Multi-language multiplies maintenance burden."
2. **API style?** "Fluent/builder pattern, functional, or imperative? What do consumers of this library expect in the target language ecosystem?"
3. **Public surface area?** "How many public classes/functions do you anticipate? Under 20 is a small library, 20-100 medium, 100+ is a framework."
4. **Configuration?** "Constructor injection, function parameters, config objects, or environment variables? Dependency injection support?"

## Consumers

5. **Consumer types?** "Internal teams only, open-source community, or enterprise customers? Each has different stability and documentation expectations."
6. **Integration points?** "Does this library wrap an external service, extend a framework, or stand alone?"
7. **Breaking change tolerance?** "How do consumers handle upgrades? Semantic versioning with deprecation windows, or can you force migrations?"

## Quality

8. **Error handling strategy?** "Exceptions, result types (Rust/Go style), callbacks, or promises? What's idiomatic for the target language?"
9. **Testing expectations?** "Unit tests only, integration tests with mock services, or property-based testing? Test coverage target?"
10. **Documentation level?** "API docs from code comments, tutorial/guide, full reference manual? Examples for common use cases?"
11. **Type safety?** "Strict typing throughout, or dynamic where convenient? Generic/type parameter support?"

## Distribution

12. **Package registry?** "npm, PyPI, Maven Central, crates.io, Go modules? Private registry needed?"
13. **Bundle size constraints?** "Tree-shakeable? Target size for browser bundles? Zero-dependency or acceptable to include transitive deps?"
14. **Platform support?** "Browser only, Node.js, both? Native bindings (C/Rust FFI)? Platform-specific code paths?"

## Lifecycle

15. **Initialization?** "Synchronous init, async init, or lazy initialization? Startup cost budget?"
16. **Resource cleanup?** "Does the library hold resources (connections, file handles)? Disposable/cleanup pattern needed?"
17. **Thread safety?** "Will instances be shared across threads? Immutable design or explicit synchronization?"
