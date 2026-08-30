---
name: artifact-template-soft-focus-color-haze
description: "Create restrained, newly composed Soft-Focus Color Haze backgrounds. Use when the user selects this template, names Soft-Focus Color Haze, or explicitly invokes $artifact-template-soft-focus-color-haze. Treat the retained PNG as a style-language reference only: vary the composition instead of copying it, and adapt the color field to support any supplied subject."
---

# Soft-Focus Color Haze

Create a fresh image in this template's visual language. Keep both retained reference files unchanged, and never use either reference's exact spatial arrangement or depicted subject as the default output.

## Workflow

1. Read `artifact-template.json` and resolve its canonical background reference relative to this skill directory. Also resolve `assets/subject-reference.png`, the dedicated subject-led style reference.
2. Determine the mode from the user's brief and supplied images:
   - **Background-only:** no person, object, product, UI, typography, or other focal element is requested.
   - **Subject-led:** the user requests or supplies a foreground subject of any kind.
   When one request asks for both modes, classify and generate each output separately. Do not let the reference choice, palette routing, or contrast logic from one output leak into the other.
3. Select exactly one mode-specific **style-only reference** for $imagegen:
   - **Background-only:** use the canonical PNG named by `artifact-template.json`.
   - **Subject-led:** use `assets/subject-reference.png` instead of the canonical background PNG.
   Do not pass both template references unless the user explicitly requests a comparison or blend. Never use either one as an edit target or composition to trace. When the user supplies a subject image, pass that image separately as the content/edit target and identify its role clearly in the generation brief.
4. Translate the user's request into the relevant rules below. In subject-led mode, treat the requested subject as a conceptual seed: describe only its broad direction, mass balance, placement, and color-temperature role. Explicitly discard anatomy, taxonomy, surface detail, photographic realism, and any assumption that the subject must grow upward from the bottom edge. Route generic color-tone requests according to the subject–field contrast rules instead of tinting the whole image one hue. Do not invent text, logos, UI, objects, or factual content merely to fill the composition.
5. In subject-led mode, resolve placement **before** calling $imagegen. If the user gives a position, follow it. Otherwise run the placement-card procedure below, write the selected card into the generation brief as a hard `COMPOSITION LOCK`, and make placement independent of the reference image, subject type, and palette. Do not use words such as “random,” “asymmetric,” or “ample negative space” as a substitute for an explicit card.
6. Visually inspect the result. Unless the user explicitly requests recognizability, reject it if the subject is instantly identifiable as a literal object or species at thumbnail size; if it contains anatomy, surface texture, a sharp focal plane, or macro-photography cues; if subject and field share the same dominant hue or temperature family and merge at thumbnail size; if its subject centroid, entry edge, or empty-space direction violates the selected composition card; if it repeats a recent subject-led layout when eligible alternatives existed; if it copies a reference layout; or if it loses the soft grain and low-frequency color language.
7. Return the final image. If the user asks for variants, make each one compositionally distinct while keeping the same restrained style grammar.

## Governing principle

Match the reference's **visual language, not its pixels, depicted flower, or layout**. Preserve softness, material feel, color relationships, and restraint. In subject-led mode, abstraction must be generative rather than a post-processing effect: construct the image from broad defocused color volumes from the outset, never from a detailed object that is blurred afterward. Randomize the placement and flow of forms on every background-only generation. Treat a reference subject only as evidence for focus, color, depth, cropping character, and broad negative-space restraint—never for anchor position—and never assume the user's subject is botanical. Copy a reference composition only when the user explicitly asks for a close remake.

## Style grammar

- Build a full-bleed abstract field from 2–4 oversized, low-frequency organic masses: broad veils, blurred folds, soft directional sweeps, or clouded color blooms. They may suggest soft material without depicting literal fabric, petals, or flowers.
- Blur every transition heavily. Use translucent, milky overlaps and feathered boundaries; avoid crisp vector edges, hard gradient stops, outlines, or sharply modeled 3D forms.
- Use 3–5 coordinated colors divided between two clearly opposed temperature or hue families. Choose one dominant field family, one contrasting subject or accent family, and at most one stronger accent. Favor powder blue, cyan, peach, coral, butter yellow, blush pink, lavender, and warm off-white; alternate palettes rather than repeating the reference's exact color placement.
- Keep global tonal contrast low to moderate while making subject–field chromatic separation unmistakable. Concentrate color energy in one controlled area and let the rest breathe. A large quiet region is part of the design, not missing detail.
- Add fine, even, tactile grain over the whole canvas: matte, softly printed, lightly frosted. Avoid coarse noise, dust, scratches, glossy CGI, lens flare, bokeh, or photographic scenery.
- Do not bake in a frame, border, card, rounded corners, or drop shadow unless the user asks. Those belong to the destination layout, not the background artwork.

## Background-only mode

- Generate a new asymmetric composition rather than an edit of the retained reference. Randomly vary the palette family, main flow direction, accent location, overlap pattern, and relative scale of the 2–4 color masses.
- Keep the randomness bounded and calm: one visual movement, one accent zone, and ample low-detail space. Do not fill every area with equal saturation or activity.
- Create no implied central object or recognizable motif. Exclude people, products, icons, text, symbols, flowers, landscapes, architecture, and decorative particles unless explicitly requested.
- Avoid reproducing the reference's diagonal, folds, hotspots, color map, or rounded silhouette one-for-one.

## Subject-led mode

Use `assets/subject-reference.png` only to establish optical softness, warm–cool separation, negative space, cropping behavior, and the relationship between a soft subject and a calm field. Its flower is not a reusable motif, layout, silhouette, or default subject. The default target is semi-abstract to near-nonrepresentational: a restrained color presence rather than an illustrated object.

### Subject identity

- Use the named or supplied subject as a semantic seed, not as an object to depict faithfully. Preserve only its broad gesture or orientation, overall mass distribution, and at most one weakened recognition cue. Exact category recognition is not required by default; ambiguity is a desired result.
- Compress the subject into one primary color mass and at most two subordinate overlaps or echoes. Merge, soften, or remove small components instead of reproducing countable parts. The viewer should sense a presence or direction before identifying a thing.
- Derive the remaining directional tendency from the subject, but simplify its geometry aggressively. Do not preserve a complete contour, internal anatomy, realistic proportions, or enough information to identify a species, model, or brand.
- Even when the requested subject is a flower, suppress petal count, flower center, stamens, veins, leaves, and botanical structure. When the subject is not a flower, never import petals, spikes, radial bloom geometry, or any other floral shorthand from the reference.

### Focus and rendering

- Build the subject directly from low-frequency, defocused color planes. Do not first render a realistic object and then apply blur. No local feature should read as a vein, filament, pore, hair, seam, printed mark, or other material evidence.
- Use graded diffusion without a sharp focal plane. The least-blurred area must still be soft, broad, and textureless; it may clarify weight or direction, but never anatomy. Let all outer boundaries dissolve through visibly wide feathered transitions so no edge reads as a cutout.
- Layer one broad opaque or semi-opaque mass with one or two softer translucent echoes. Allow gentle color bleed between them, but avoid a uniform Gaussian blur, obvious directional motion streaks, or a shapeless fog bank. The form should have weight without literal detail.
- Treat the subject as luminous matte pigment seen through diffusion: no macro-photography look, realistic lens depth of field, naturalistic lighting, specular highlights, outlines, black cast shadows, or detailed material texture. A small muted complementary shadow may anchor the mass without describing a physical surface.
- Keep grain fine and continuous across the canvas. Grain is atmospheric and must never turn into visible texture on the subject.

### Composition

- Use one ambiguous subject mass against a continuous, uncluttered field. Give it roughly one-third to one-half of the visual weight and leave at least about half of the frame as calm, low-detail negative space.
- Treat the subject as suspended color, not as an object standing on a floor or growing from the bottom. A flower prompt must not imply a stem, ground, gravitational base, lower-edge entry, or lower-left placement. Do not default to a centered radial arrangement merely because the semantic seed is botanical.
- Cropping may make the image feel intimate and atmospheric. Keep only the main directional cue inside the frame; do not reveal more of the object merely to explain what it is. The crop, scale, orientation, and empty-space side come from the selected composition card, never from the reference image.
- Omit scenery, ground planes, supporting props, decorative particles, and extra subjects unless requested. The relationship is a single soft subject suspended in a calm color field.

### Placement-card procedure

Use this procedure whenever the user has not specified subject placement. It exists to prevent the common model shortcut of repeatedly placing a warm mass in the lower-left with empty space above and to the right.

1. Inspect the subject-led outputs visible in the current conversation. For up to the three most recent outputs, note the subject's approximate 3×3 anchor zone, cropped edge or edges, main flow direction, and side of the largest empty region. Treat mirrored or slightly shifted versions of the same arrangement as repetitions.
2. Put an exact anchor zone on cooldown if it appears in any of those three outputs. If the same row or column appears at least twice, put that entire row or column on cooldown for the next selection when another option is available. If one corner repeats, the next two outputs must use both a different row and a different column. In the specific failure pattern of repeated lower-left outputs, temporarily exclude the lower row, the left column, bottom entry, and left entry; do not merely move the same mass a few pixels inward.
3. Build the eligible deck from the cards below after applying cooldowns. Select from the eligible cards with genuine nondeterministic entropy rather than choosing the first, most familiar, or semantically “natural” option. When shell access is available, actually read a value from `/dev/urandom` (for example `od -An -N2 -tu2 /dev/urandom`) and use that value modulo the eligible-card count; do not choose intuitively and then call the choice random. If no random primitive is available, rotate away from all recent rows, columns, crop edges, and empty-space directions and select the least recently represented card.
4. Independently choose one scale token—`compact` (about 20–30% of frame area), `medium` (30–42%), or `large-cropped` (42–55%)—while avoiding the immediately previous scale when possible. The style reference does not choose the scale.
5. Add one explicit line to the $imagegen brief: `COMPOSITION LOCK — card [ID], [anchor and crop], [flow], [empty-space side], scale [token]. Treat this as a hard spatial constraint. Ignore the reference image's subject position and do not relocate the subject away from this locked zone.` Replace the bracketed fields with the selected values. For every card except G, append `Do not place any primary subject mass in the lower-left quadrant.` Do not expose the internal card selection unless the user asks.

The composition deck is deliberately balanced across the frame:

- **A — upper-left entry:** centroid near `(22%, 20%)`; crop top and/or left; flow down-right; largest quiet region lower-right.
- **B — upper-center entry:** centroid near `(50%, 18%)`; crop top; flow downward or down-diagonal; largest quiet region across the lower half.
- **C — upper-right entry:** centroid near `(78%, 20%)`; crop top and/or right; flow down-left; largest quiet region lower-left.
- **D — middle-left entry:** centroid near `(18%, 50%)`; crop left; flow inward or gently rightward; largest quiet region on the right.
- **E — center-offset suspension:** centroid near `(45–55%, 42–58%)`; no edge crop; non-radial horizontal or diagonal gesture; a broad quiet perimeter rather than one default corner.
- **F — middle-right entry:** centroid near `(82%, 50%)`; crop right; flow inward or gently leftward; largest quiet region on the left.
- **G — lower-left entry:** centroid near `(22%, 80%)`; crop bottom and/or left; flow up-right; largest quiet region upper-right. This is one option only, never the default.
- **H — lower-center entry:** centroid near `(50%, 82%)`; crop bottom; flow upward or up-diagonal; largest quiet region across the upper half.
- **I — lower-right entry:** centroid near `(78%, 80%)`; crop bottom and/or right; flow up-left; largest quiet region upper-left.
- **J — diagonal passage:** centroid near the middle third; one end may leave the frame; alternate northwest-to-southeast and northeast-to-southwest flow; keep the largest quiet region on only one side of that diagonal. Do not turn this into a centered radial burst.

For multiple subject-led outputs in one request, draw cards without replacement. Two outputs must differ in both grid row and grid column whenever possible. Three outputs must cover all three rows (upper, middle, lower) and at least two columns (left, center, right), use different entry/crop edges, and place their largest quiet regions on different sides. If a recent-output cooldown makes three-row coverage impossible, preserve the cooldown and cover every remaining eligible row instead. Color changes, mirroring, or minor coordinate shifts do not count as compositional variation.

After generation, estimate the visible subject centroid and touched frame edges. If they do not match the locked card, or if the result falls into a cooled-down zone, regenerate with the card restated and an explicit negative constraint naming the unwanted zone. A result that is beautiful but ignores the lock does not pass.

### Color hierarchy

- Use a dominant, nearly continuous background field from one hue family, with only subtle low-frequency tonal drift. Keep the area immediately around the subject locally simple and free of competing accents.
- Give the subject a compact family of 2–3 blended hues from an opposing temperature or hue family: one dominant body color, one quieter transition, and optionally one restrained accent. Do not repeat the field's dominant hue inside most of the subject.
- Follow the role asymmetry visible in `assets/subject-reference.png`: a broad, stable, lower-complexity field supports a smaller, more chromatic subject mass. The strong default is cyan, sky blue, or pale periwinkle behind coral, orange, butter yellow, blush, or warm off-white.
- Include one restrained anchoring zone inside the subject that is modestly deeper or denser than the field, plus at most one light area. This internal span gives the blurred mass weight without creating a hard shadow or photographic modeling.
- Separate subject and field through clear hue or temperature opposition **and** at least one secondary axis: higher subject saturation or a modest lightness difference. Do not solve weak separation with a sharp outline, hard shadow, or extra detail.
- Concentrate the strongest color energy inside or immediately beside the subject, then let it dissolve outward. Preserve the opposing color identity through the feathered transition instead of blending the entire perimeter into the field hue. Do not scatter equal-intensity accents around the canvas or create a hard glowing halo.

### Subject–field contrast gate

- Soft edges are mandatory; weak separation is not. At thumbnail size or while squinting, the subject must remain a distinct color mass against the field even though no contour is sharp.
- Never default to analogous-on-analogous pairings such as blue or violet subject on a blue field, or yellow or orange subject on a yellow field. Use those only when the user explicitly requests monochrome, and then create separation through a deliberate light–dark and saturation split.
- For a generic cool-tone request such as “blue-toned,” assign the requested cool family to the background field and give the subject a restrained warm opponent such as orange, coral, yellow, blush, or cream.
- For a generic warm-tone request such as “yellow-toned,” assign the requested warm family to the subject and keep the field cool, typically cyan, pale blue, or periwinkle. A background-only output may use the requested warm hue as its field because it has no subject–field separation requirement.
- If the user explicitly assigns a color to the background, choose an opposing subject family. If the user explicitly assigns a color to the subject, choose an opposing, calmer field. Honor an explicit monochrome request only after preserving a readable value and saturation hierarchy.
- Useful opponent relationships include cyan–orange, sky blue–coral, periwinkle–butter yellow, lavender–warm yellow, blush–teal, and pale yellow–blue violet. Vary the exact hues and proportions; do not reproduce the reference's color coordinates.
- If the subject disappears into the field, change the palette roles or chroma/value relationship. Do not sharpen the shape, add an outline, or increase literal detail.

### Restraint budget

- Limit the image to one dominant background field, one primary subject mass, no more than two subordinate echoes, 2–3 subject hues, and a single accent zone.
- Keep all information at a large scale. Remove fine lines, repeated ridges, small holes, countable appendages, realistic highlights, and local contrast events.
- Use temperature and saturation to imply the subject; do not explain it with contour, anatomy, texture, scenery, or a literal light source.
- Apply the thumbnail test: if a viewer can immediately name the species, object model, or material because of visible detail, the result is too literal. If the image reads first as a restrained color presence with only a faint semantic suggestion, the abstraction level is correct.

### Legibility-critical subjects

- Use this exception only when the user explicitly requires readable text, usable UI, identity fidelity, or precise product geometry. Do not infer that requirement merely because such content is present; the default subject-led treatment remains ambiguous and non-representational.
- When this exception is explicitly requested, preserve only the critical pixels and contours needed for recognition or use. Apply the diffused color-volume treatment to noncritical surfaces and to a soft atmospheric echo behind the subject instead of blurring essential content.
- Keep text and controls readable, faces recognizable, and product-defining geometry intact. Never invent labels, icons, interface chrome, facial features, or brand details.
- When the result will be placed inside a rounded card, generate it full-bleed and let the destination layout clip it unless the user explicitly requests baked-in corners.

## Fidelity

Preserve the mode-specific reference's relevant style cues. In background-only mode, follow the canonical reference's low-frequency layering, translucent material treatment, matte grain, and quiet hierarchy. In subject-led mode, follow `assets/subject-reference.png` for graded defocus, a calm dominant field, clear opponent chromatic separation that survives at thumbnail size, asymmetric cropping, and negative space. Its subject location, crop edge, empty-space direction, orientation, and scale carry zero compositional authority; those come only from the user's instruction or the placement-card procedure. Do **not** preserve either reference's exact composition, depicted subject, geometry, color coordinates, or crop.

User instructions control requested content and explicit deviations. Where the user is silent, these style rules control the result while composition remains freshly generated.
