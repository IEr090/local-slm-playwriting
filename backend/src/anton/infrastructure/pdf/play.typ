// Template of the PDF of the finished play. The play comes in as JSON (sys.inputs.play) and is only ever
// shown with text(): the words of the play are never put into markup, so #, *, _, $, [ ], @ stay as written.

#let play = json(bytes(sys.inputs.at("play")))

#let ink = rgb("#1c1a16")
#let gold = rgb("#8a6d2f")
#let serif = "Cormorant Garamond"
#let sans = "Jost"

// A string with its line breaks kept, set as text.
#let literal(value) = {
  let lines = value.split("\n")
  for (index, line) in lines.enumerate() {
    if index > 0 { linebreak() }
    text(line)
  }
}

#let capitalized(word) = upper(word.first()) + word.slice(1)

#let letter-spaced(body, size: 8.5pt, fill: ink, weight: 500) = text(
  font: sans, size: size, tracking: 0.18em, weight: weight, fill: fill, body,
)

#set document(title: play.title)
#set text(font: serif, size: 12.5pt, fill: ink, lang: play.language_code, hyphenate: true)
#set par(leading: 0.95em, justify: false, spacing: 1em)
#set page(
  paper: "a4",
  fill: white,
  margin: (top: 25mm, bottom: 25mm, x: 22mm),
  header: context {
    let starts = query(<act-start>)
    if starts.len() > 0 and here().page() >= starts.first().location().page() {
      align(right, text(font: sans, size: 8pt, tracking: 0.08em, fill: gold, play.title))
    }
  },
  footer: context {
    if here().page() > 1 {
      align(center, text(font: sans, size: 9pt, fill: ink, counter(page).display()))
    }
  },
)

// Title page
#align(center + horizon)[
  #text(size: 36pt, weight: 500, play.title)
  #v(1.2em)
  #text(size: 15pt, style: "italic", [A #play.genre in #play.act_count_word acts])
  #v(2.2em)
  #block(width: 78%, text(size: 11pt, literal(play.premise)))
]

// Dramatis Personae
#pagebreak()
#v(1fr)
#align(center, letter-spaced(fill: gold, [DRAMATIS PERSONAE]))
#v(1.6em)
#for member in play.cast {
  grid(
    columns: (38%, 1fr),
    column-gutter: 1.2em,
    align: (right + top, left + top),
    block(above: 0.2em, below: 0.9em, letter-spaced(size: 8.5pt, text(member.name))),
    block(above: 0em, below: 0.9em, text(size: 13pt, literal(member.description))),
  )
}
#v(2em)
#align(center, text(size: 12.5pt, style: "italic", literal(play.time_and_world)))
#v(2fr)

// Speeches and stage directions
#let show-block(block) = {
  if block.kind == "direction" {
    return std.block(above: 1.1em, below: 1.1em, text(size: 11.5pt, style: "italic", literal(block.text)))
  }
  if block.kind == "plain" {
    return std.block(above: 1em, below: 1em, literal(block.text))
  }
  // the speaker sticks to the start of the speech, so a name never stays alone at the bottom of a page
  std.block(sticky: true, above: 1.5em, below: 0.7em, {
    letter-spaced(block.speaker)
    if block.note != "" {
      [ ]
      text(size: 11.5pt, style: "italic", "(" + block.note + ")")
    }
  })
  std.block(above: 0em, below: 0.4em, text(size: 12.5pt, literal(block.text)))
}

#let show-scene(scene) = {
  align(center, {
    v(2em)
    letter-spaced(fill: gold, [SCENE #scene.number])
    if scene.place_name != "" {
      linebreak()
      v(0.2em)
      text(size: 14pt, style: "italic", scene.place_name)
    }
  })
  v(0.6em)
  for block in scene.blocks { show-block(block) }
}

#for act in play.acts {
  pagebreak(weak: true)
  [#metadata(none) <act-start>]
  v(2em)
  align(center, text(size: 24pt, weight: 500, [Act #capitalized(act.number_word)]))
  for scene in act.scenes { show-scene(scene) }
}

// The end
#v(3em)
#align(center)[
  #text(size: 15pt, style: "italic", [Curtain.])
  #v(1em)
  #letter-spaced(size: 9pt, [THE END])
]
