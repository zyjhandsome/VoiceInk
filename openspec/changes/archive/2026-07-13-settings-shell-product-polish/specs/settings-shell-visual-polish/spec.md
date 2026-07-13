## ADDED Requirements

### Requirement: Settings shell has clear product surface hierarchy
The settings window SHALL present a clear visual hierarchy between sidebar, page content, section groups, and footer, while remaining on the classic cool-neutral palette (no warm cream theme, no purple theme, no dark settings theme).

#### Scenario: Open settings general page
- **WHEN** the user opens Settings and lands on the General page
- **THEN** the page title and subtitle remain readable as the primary content header
- **AND** setting sections appear as distinct grouped surfaces on the cool gray canvas (not as a flat undifferentiated field)
- **AND** the footer remains visually secondary to content, with the primary close action still the strongest CTA

#### Scenario: Shared tokens do not break classic cool axis
- **WHEN** settings shell tokens are adjusted for product-feel surfaces
- **THEN** the settings background, surfaces, hairlines, and text remain on a single cool gray/blue axis
- **AND** no warm-pearl or purple-gradient theme is introduced

### Requirement: Navigation selection is obvious without overusing brand blue
The settings sidebar SHALL make the active page unmistakable, using at most one strong brand-blue accent device plus a restrained selected wash; navigation label text MUST remain dark/neutral when selected (not blue-on-blue text).

#### Scenario: Switch between settings pages
- **WHEN** the user selects 模型 after 通用
- **THEN** the Model nav item shows a clear selected state distinct from idle items
- **AND** the Model page becomes visible
- **AND** brand blue is not applied simultaneously as selected text color plus saturated fill plus thick border on the same nav item

### Requirement: Interactive choice cards show restrained selected state
Trigger-mode and equivalent choice cards in settings SHALL show a restrained selected state (left accent or thin accent edge plus soft wash) and MUST NOT use a triple-emphasis selected look (saturated blue fill + blue border + blue title text together).

#### Scenario: Select continuous trigger mode
- **WHEN** the user chooses「自动持续转写」
- **THEN** that card is visually selected relative to「按住快捷键录音」
- **AND** the selected treatment uses at most one strong blue accent device plus soft wash
- **AND** the underlying trigger-mode setting value still updates as today (behavior unchanged)

### Requirement: Focus and affordances remain readable
Keyboard focus rings and primary actions in the settings shell MUST remain visibly distinct from idle chrome after the visual polish.

#### Scenario: Focus a hotkey field or nav item
- **WHEN** keyboard focus moves to an interactive settings control that previously had a focus ring
- **THEN** a visible focus treatment remains present
- **AND** the primary footer close button remains the dominant filled action

### Requirement: Configuration semantics stay unchanged
This change MUST NOT alter settings information architecture, setting keys, persistence timing, or user-visible setting labels/copy except where a purely visual container requires no copy change.

#### Scenario: Persist a general setting after polish
- **WHEN** the user changes a General setting that previously took effect immediately
- **THEN** the value still persists immediately with the same semantics
- **AND** the four pages remain 通用 / 模型 / 润色 / 关于

#### Scenario: Out-of-scope surfaces are not redesigned in this change
- **WHEN** this change is implemented
- **THEN** floating window, history window, and tray menu are not given a new visual language in the same change
- **AND** any shared token edits leave those surfaces functionally intact and without a conflicting new theme
