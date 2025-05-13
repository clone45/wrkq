Thanks, Bret. I’ll gather and compile a comprehensive markdown document listing all the CSS properties, selectors, and styling features supported by the latest version of the Python Textual library. This will include layout, borders, colors, animations, and anything else officially supported.

I'll let you know once it's ready to download.


# Textual CSS Reference: Properties, Selectors & Styling Features

## CSS Selectors in Textual

Textual uses a CSS-like syntax to style widgets by their type, identifiers, classes, state, and hierarchy. The supported selectors include:

* **Type Selectors:** Use the widget’s class name to select all instances of that widget type. For example, `Header { ... }` targets all widgets of class `Header`.
* **ID Selectors:** Prefix with `#` to target a widget by its unique ID (set via `id="..."` in code). E.g. `#submitButton { ... }` styles the widget with `id="submitButton"`.
* **Class Selectors:** Prefix with `.` to target widgets by custom class names (set via `classes="..."`). E.g. `.highlight { color: yellow; }` applies to any widget with class “highlight.”
* **Universal Selector:** `*` matches all widgets (or all children when combined with a parent selector). For example, `VerticalScroll * { background: red; }` would make all children of a `VerticalScroll` widget have a red background.
* **Combinators:** Support descendant (space) and child (`>`) combinators for hierarchy. A selector like `Container Button { ... }` matches `Button` widgets anywhere inside a `Container`. Using `>` (child) like `Container > Button { ... }` matches only direct children.
* **Pseudo-Classes:** Textual defines pseudo-classes to style widgets in certain states. For example, `Button:hover { background: green; }` applies when a widget is hovered by mouse. Supported pseudo-classes include:

  * `:hover` – Mouse is over the widget
  * `:focus` / `:blur` – Widget has (or doesn’t have) input focus
  * `:enabled` / `:disabled` – Enabled/disabled state
  * `:first-child` / `:last-child` – First or last among siblings
  * `:first-of-type` / `:last-of-type` – First or last of its widget type among siblings
  * `:even` / `:odd` – Even or odd indexed siblings
  * `:focus-within` – Widget has a focused descendant
  * `:dark` / `:light` – Matches if the app’s current theme is dark or light
  * `:inline` – The app is running in inline mode (embedded in a terminal/console)
* **Specificity & Important:** Selector specificity works similarly to web CSS (ID > class/pseudo-class > type). You can append `!important` to a style rule to override others, if necessary. For example: `color: red !important;` will win over non-`!important` rules.

## Layout & Positioning

Textual provides layout properties to control how widgets are arranged and positioned:

* **`layout`:** Controls how a container widget lays out its children. Supported values: `vertical` (stack children top-to-bottom, default), `horizontal` (left-to-right), or `grid` (use explicit grid settings). For example, `#dashboard { layout: horizontal; }` will arrange all direct children of the widget with ID “dashboard” in a row.
* **`dock`:** Pins a widget to one side of its parent (or screen). Allowed values: `"top"`, `"right"`, `"bottom"`, or `"left"`. A docked widget is taken out of normal flow and “docks” to that edge. For instance, `Header { dock: top; }` attaches all `Header` widgets to the top.
* **`position`:** Controls relative vs absolute positioning of a widget. By default it’s `"relative"`, meaning the widget is placed normally and `offset` moves it relative to its normal position. If set to `"absolute"`, the widget is removed from flow and positioned relative to the top-left of its parent container. An absolutely positioned widget’s `offset` is interpreted from the container’s origin.
* **`offset`, `offset-x`, `offset-y`:** Moves a widget from its default position. You can specify two values (`offset: X Y;`) for horizontal and vertical offsets, or use `offset-x`/`offset-y` individually. For example, `offset: 4 2;` moves the widget 4 cells right and 2 lines down. Offsets apply on top of normal layout (for relative) or from container origin (for absolute). Negative values move left/up.
* **`display`:** Either `block` (render normally) or `none` to remove the widget from layout and not display it. Using `display: none` will hide the widget entirely (as if it isn’t in the DOM).
* **`layers` and `layer`:** Enables layered stacking of widgets (for overlap or z-index-like behavior). A container can define named layers via the `layers` property (e.g. `layers: base overlay;` to define two stacking layers). Child widgets can then specify `layer: overlay;` (using one of the names) to render on that layer. Layers defined by an ancestor establish a stacking context; widgets assigned to a higher layer will appear above those on lower layers.
* **`box-sizing`:** Chooses how width/height dimensions are interpreted. `border-box` (default) means the specified `width`/`height` includes content + padding + border. `content-box` means `width`/`height` apply to content only (padding and border add extra size). For example, a widget with padding will appear larger with `content-box` sizing (since it adds padding outside the content area).

## Sizing & Spacing

Control the dimensions of widgets and the spacing around/within them:

* **`width` & `height`:** Set a widget’s size. You can use absolute integers (number of text cells), percentages of the parent size, or fractional units. For example, `width: 50%;` makes the widget half as wide as its container, and `height: 1fr;` can allocate one proportional unit of remaining space (fractions distribute space among siblings). The keyword `auto` lets the widget size to its content or context (e.g. `height: auto;` allows height to expand as needed).
* **`min-width`, `min-height` / `max-width`, `max-height`:** Constrain a widget’s size to a range. They accept the same units as width/height. For instance, `max-width: 50;` ensures the widget never exceeds 50 cells in width.
* **`margin`:** Outside spacing. Like CSS, you can specify one value for all sides, two for vertical/horizontal, or four for top/right/bottom/left (e.g. `margin: 1 2;` for 1 cell top/bottom and 2 left/right). Margin does not collapse and always adds empty space outside the widget.
* **`padding`:** Inner spacing between the widget’s content and its border. Syntax is similar to margin (one, two, or four values). For example, `padding: 1;` adds a one-cell padding on all sides, while `padding: 1 0 1 0;` would add vertical padding but no horizontal padding. Padding is included in the widget’s size if `box-sizing: border-box` (default).
* **`overflow`, `overflow-x`, `overflow-y`:** Controls scroll behavior when content exceeds the widget’s area. You can set horizontal/vertical overflow together or separately. Values: `auto` (default; show scrollbars automatically when needed) or `hidden` (clip overflow content) or `scroll` (always allow scrolling). For example, `overflow-y: hidden;` will hide any vertical overflow (no scrollbar). Using `auto` vs `stable` scrollbar gutter (see below) will affect layout changes when scrollbars appear.
* **`scrollbar-gutter`:** Reserves space for a scrollbar to prevent layout shift. Values: `auto` (no reservation; content area will shrink when scrollbar appears) or `stable` (always reserve scrollbar width). Using `stable` keeps a blank gap for a scrollbar even if content doesn’t overflow, so that if one appears, the layout remains unchanged.
* **`scrollbar-size`:** Sets the thickness of scrollbars. You can typically specify a size in cells (character columns). (Horizontal and vertical scrollbar dimensions may be separately configurable; e.g., some versions support `scrollbar-size-horizontal` and `scrollbar-size-vertical` if needed.) For example, `scrollbar-size: 2;` would make scrollbars 2 cells thick.

## Color & Background

Textual supports rich color styling, including 24-bit color and transparency blending:

* **`color`:** The foreground text color of a widget. Accepts named colors (`red`, `green`, etc.), hex codes, `rgb(...)`/`hsl(...)` functions, theme variables (like `$primary`), or the special value `auto`. Using `color: auto;` will automatically choose a contrasting light or dark text color based on the widget’s background for readability. For example, on a dark background `auto` yields a light text color.
* **`background`:** The widget’s background color. Supports the same color formats as `color`, and can include an optional opacity percentage. For instance, `background: blue 50%;` sets a semi-transparent blue background (50% opacity). You can use transparency to allow underlying colors (or background images/hatches) to show through.
* **`background-tint`:** Tints (blends) the widget’s existing background with another color. For example, `background-tint: orange 30%;` would overlay a semi-transparent orange on the current background. This is useful for subtly changing a background’s hue or emphasis without fully overriding it.
* **`tint`:** Similar to background-tint, but applies a color blend *over the entire widget (including its content)*. This effectively places a translucent color filter on the widget. For instance, a red tint with 20% opacity (`tint: red 20%;`) could indicate an error state by tinting the widget red without completely obscuring its content.
* **`hatch`:** Fills the widget’s background with a repeating hatch pattern for texture. The value is a hatch style and an optional color. Available `<hatch>` patterns include `horizontal`, `vertical`, `cross` (diagonal crosshatch), `left` or `right` (single diagonal). For example, `hatch: cross gray;` would draw a gray cross-hatch pattern over the widget’s background.
* **Color Formats & Variables:** Colors can be specified by name, hex (`#RRGGBB` or `#RGB`), RGB/RGBA, HSL/HSLA, etc.. Textual also provides **theme color variables** (prefixed with `$`) that adapt to the current theme, such as `$primary`, `$secondary`, `$accent`, `$foreground` (text color), `$background`, etc. These variables are defined by the active theme (and can be customized or overridden) and ensure your app’s colors are consistent. For example, you might use `$text` and `$surface` variables instead of hardcoding specific colors. Theme variables often come in pairs like `$text-primary` / `$primary` and muted variants like `$primary-muted` for lighter/darker shades.

## Borders & Outlines

You can draw borders and outlines around widgets, with various styles:

* **`border`:** Draws a border on all sides of a widget. You can specify a **border style** and **color**, plus an optional opacity percentage to blend the border with the background. For example, `border: solid red;` draws a solid red border. Textual comes with many border styles (e.g. `ascii`, `round`, `heavy`, `double`, `dashed`, `outer`, `inner`, etc.). You may also apply borders to individual sides with `border-top`, `border-right`, `border-bottom`, `border-left` if needed (each takes the same values as `border`). Borders occupy space (affect layout), unless using an overlapping outline (see below). *Note:* A border and an outline cannot coexist on the same edge of a widget.
* **Border Title & Subtitle:** Widgets can display a text label within their top border (`border_title`) or bottom border (`border_subtitle`). There are CSS properties to style these:

  * `border-title-align`: alignment of the title text (`left`, `center`, or `right`; default left). Similarly, `border-subtitle-align` (default right).
  * `border-title-color` / `border-subtitle-color`: text color for the border title/subtitle.
  * `border-title-background` / `border-subtitle-background`: background color behind the title/subtitle text (useful if the border has a tinted background).
  * `border-title-style` / `border-subtitle-style`: text style for the labels (e.g. bold, italic, etc., same values as `text-style`).
    These properties let you, for example, center a border title and make it bold: `border-title-align: center; border-title-style: bold;`.
* **`outline`:** Similar to a border but drawn as an overlay on the widget’s content area. An outline does **not** consume layout space; it is rendered on top of the widget (inside the padding area). The syntax is like `border`: specify an outline style and color (e.g. `outline: heavy white;`). You can target individual sides with `outline-top` etc., as well. Outlines are often used to indicate focus (for example, Textual’s default focus highlight on a widget is an outline). Because it’s drawn over content, an outline may obscure part of the widget’s contents if thick or if padding is small.
* **Border/Outline Styles:** The `<border>` style type in Textual includes a variety of predefined line art styles. Examples: `ascii` (plain ASCII `+--+` style), `round` (rounded corners), `solid` (single line), `double` (double line box), `dashed` (dashed line), `heavy` (thick line), `inner`/`outer` (half lines for combined borders), `hidden` (no visible line), and others. These can be used for both `border` and `outline`. You can preview available border styles using the CLI command `textual borders`.
* **`keyline`:** Draws divider lines between child widgets inside a container (often used in list or grid layouts for separators). A keyline is essentially a single line (top border) of a given style and color. Values use the `<keyline>` type: `none` (no line), `thin`, `heavy`, or `double`, plus a color. For example, a Vertical list might use `keyline: thin $surface;` to draw a thin line between each item (the keyline appears at the bottom of each child). Keylines are useful for delineating sections or rows within containers.

## Scrollbar Styling

Scrollbars in Textual can be styled via CSS as well:

* **`scrollbar-color` and `scrollbar-background`:** These set the color of the scrollbar **thumb** (the draggable handle) and **track** (the background trough) respectively. You can also specify state-specific variants: `scrollbar-color-hover` / `scrollbar-background-hover` for when the mouse is over the scrollbar, and `scrollbar-color-active` / `scrollbar-background-active` for when the scrollbar is being dragged. For example, to style a blue scrollbar you might use: `scrollbar-background: #333; scrollbar-color: cornflowerblue; scrollbar-color-hover: lightblue;`.
* **`scrollbar-corner-color`:** Color of the corner square where a horizontal and vertical scrollbar meet (at the bottom-right of a scrollable area, if both scrollbars are present). This is usually set to match the track or background color.
* **`scrollbar-gutter`:** (See **Sizing & Spacing** above) Controls whether space for a scrollbar is reserved.
* **`scrollbar-size`:** Sets the thickness of the scrollbar. For example, a larger area for easier mouse use can be done with `scrollbar-size: 3;` (making it 3 text cells wide/tall). There may be separate `scrollbar-size-horizontal`/`scrollbar-size-vertical` controls if needed, but by default a single value applies to both dimensions.

## Text & Typography

While running in a text terminal, Textual doesn’t support font families or sizes (it uses the terminal’s monospaced font), but it provides properties to style and align text content:

* **`text-align`:** Aligns multiline text within a widget (similar to CSS `text-align`). Values: `left`, `center`, `right`, or `justify`. This affects how lines of text are aligned horizontally. For example, a `Label` with `text-align: center;` will center each line of its text within the label’s width. `justify` will spread text to fill the width. (The default alignment is `start`, which is typically left-aligned.)
* **`content-align`:** Aligns the widget’s *content area* within its own box. This takes two values: a horizontal alignment (`left`, `center`, `right`) and a vertical alignment (`top`, `middle`, `bottom`). For example, `content-align: center middle;` centers the widget’s content horizontally and vertically inside itself (useful if the widget has extra space). This is often used to center a single-line label within a larger cell.
* **`text-wrap`:** Controls wrapping of text when it exceeds the width. Values: `wrap` (default, break long text onto new lines) or `nowrap` (disable wrapping). If `nowrap` is set, overflow text will stay on one line (and likely be cut off or cause a horizontal scroll if the container is scrollable).
* **`text-overflow`:** Specifies how to render text that cannot fit in one line, when wrapping is disabled or a single line is too long. Options: `clip` (simply cut off overflowing text), `ellipsis` (replace overflow with `…` character), or `fold` (visually “fold” the overflow onto the next line without actually increasing content height). For instance, with `nowrap` and `text-overflow: ellipsis;`, an overlong line will end in “…” when it doesn’t fit.
* **`text-style`:** Sets stylistic attributes for the text (similar to font-weight or text-decoration in web CSS, but terminal-specific). Multiple styles can be combined by listing them space-separated. Supported values: `bold`, `italic`, `underline` (underlined text), `strike` (strikethrough ~~text~~), `reverse` (swap foreground/background colors), or `none` (no special style). For example: `text-style: bold underline;` makes text bold and underlined. These styles affect how text is rendered in the terminal (using ANSI styles).
* **`text-opacity`:** Adjusts the opacity of the text *foreground color* only (not affecting the background). Accepts a number 0.0–1.0 or percentage. Since true alpha blending of text isn’t possible in most terminals, Textual approximates this by blending the text color with the background. For instance, `text-opacity: 50%;` on white text over a black background would render the text as a medium gray (50% blend of white on black). This is useful for dimming text without changing the background. (Note that `opacity` vs `text-opacity`: the former fades the entire widget including background; the latter only fades the text color.)
* **`opacity`:** (Not strictly text-only, but related) Sets the opacity for the entire widget (text and background). As with text-opacity, this is an approximation in terminals: the widget’s content is blended with the parent background to simulate transparency. `opacity: 0` makes a widget fully transparent (effectively invisible), intermediate values produce see-through blending.

## Theming & CSS Variables

Textual’s theming system allows you to define a cohesive color scheme and switch between light/dark modes easily:

* **Themes and Base Colors:** Textual comes with default themes (e.g. “textual-dark” and “textual-light”) which define a palette of variables. Key theme color variables include `$primary` (primary brand color), `$secondary` (secondary color), `$accent` (attention-grabbing accent), `$foreground` / `$text` (main text color), `$background` (main background color), and semantic colors like `$success`, `$warning`, `$error`, etc. Each of these may also have tinted variants (e.g. `$primary-muted` for a muted version, `$text-primary` for a text color optimized to display on primary). By using these variables in your CSS (e.g. `color: $foreground; background: $background;`), your app automatically adapts when the theme changes or when the user switches between light and dark mode.
* **Dark/Light Mode:** Textual themes designate whether they are “dark” or “light” (`App.theme.dark` boolean). In CSS, you can target these via the `:dark` or `:light` pseudo-classes. This allows for conditional styling. For example:

  ```css
  Button:dark { background: $accent; }
  Button:light { background: $secondary; }
  ```

  This would use a different button color depending on the active theme mode. (Often, though, using the theme variables directly is sufficient, as those variables already differ between the dark and light theme definitions.)
* **CSS Variables:** You can define custom variables in Textual CSS similar to web CSS custom properties. For instance, you might see `$mycolor: steelblue;` in a theme file, or use `--my-var: value;` syntax (if supported) to define app-specific constants. Standard CSS `var(--name)` usage is supported for these custom properties. (Theme variables with `$` are substituted by the theme system rather than via `var()` function.) In practice, app-specific theming is usually done by registering a new theme or overriding variables in Python, but you can also reference custom properties in your CSS if needed.
* **Themes API:** Although not part of CSS syntax, note that you can programmatically switch themes (e.g. `App.set_theme("textual-light")`) or register new themes in Python. The CSS you write can leverage the theme’s variables so that a theme swap automatically updates styles. The `:dark`/`:light` pseudo-classes also respond to theme changes dynamically.
* **Default Styling and Inheritance:** Many Textual widgets come with default CSS (often provided via a `DEFAULT_CSS` class attribute). Your app CSS can override these. If two rules conflict, normal CSS cascade and specificity rules apply. Using `!important` can force an override if absolutely needed. Also, CSS rules can cascade down the DOM – e.g., setting a `color` on a container will typically inherit to child text unless those children override it. Theme variables for text (like `$text`, `$text-muted`) are designed to ensure sufficient contrast against background variables (like `$surface`, `$background-muted`), so leveraging them helps maintain readability.

## Animations & Transitions

While not expressed via CSS properties, Textual has a built-in **animation system** to animate style changes. You can animate many of the above style properties (such as position offsets, size, colors, opacity, etc.) with smooth transitions:

* **Animating Styles:** Both `App` and `Widget` objects have an `animate` method, and the `styles` object on each widget has the same. This allows you to interpolate a style property from its current value to a new value over time. For example, to fade out a widget you could do: `widget.styles.animate("opacity", value=0.0, duration=2.0)`, which will gradually change the widget’s opacity to 0 over 2 seconds. Similarly you might animate `offset` to move a widget, or `background` color to blend between colors.
* **Easing & Timing:** The `animate` method supports an easing function parameter (like linear, ease-in, etc.) to control acceleration, and you can supply a delay or callback for when the animation completes. By default animations run at 60fps if possible, updating the style incrementally.
* **Examples:** In CSS, you can’t declare keyframes; instead you initiate animations in Python. But the effect is similar to CSS transitions. For instance, to smoothly slide a widget into view, you might set `position: absolute; offset: -20 0;` initially, then animate `offset` to `0 0`. Or to highlight a change, animate `background` from transparent to yellow and back. Animations are a powerful *styling feature* in Textual, used for visual effects such as expanding/collapsing, fading modals, or moving focus highlights.

---

**Sources:** The information above is based on the official Textual documentation and guides. This comprehensive list covers the CSS properties, selectors, and styling mechanisms supported in the latest version of **Textual** (a Python TUI library), including layout options, color and theme management, border styles, spacing, text styling, and dynamic visual effects.
