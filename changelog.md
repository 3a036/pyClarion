# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `CategoricalSelector` object for categorical choices (essentially a boltzmann selector but on log strengths).
- `ConstructRealizer.clear_activations()` for resetting agent/construct output state.
- multiindexing for `AgentRealizer` members.
- functions `make_realizer`, `make_subsystem`, `make_agent` for initializing empty realizers from symbolic templates.
- `ConstructRealizer.ready()` method signaling whether realizer initalization is complete.
- `ConstructRealizer.missing()` and `ContainerConstructRealizer.missing_recursive()` for identifying missing realizer components.
- `SubsystemRealizer` and `AgentRealizer` automatically connect member realizers 
upon insertion (using data present in members' construct symbols) and disconnect
them upon deletion. 
- `BufferRealizer.propagate()` docs now contain a warning about potential unexpected/unwanted behavior.

### Changed

- `SimpleBoltzmannSelector` renamed `BoltzmannSelector`
- Additional `ConstructRealizer` subclass initialization arguments now optional.
- `Behavior`, `Buffer` and `Response` factories assign `BehaviorID`, 
`BufferID`, and `ResponseID` tuples as construct identifiers.
- `Appraisal` construct renamed `Response` to avoid association with appraisal theory.

### Fixed

- Bug in `SubsystemRealizer` allowing connections between constructs that should not be linked.
- Bug in `ConstantSource` allowing mutation of output activation packets. 

### Removed

- Dependency on `numpy`.
