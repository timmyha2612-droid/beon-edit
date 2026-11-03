#!/usr/bin/env python3
"""Generate the Fluid Reveal (letters), Fluid Reveal Words and Beon Name Title presets for DaVinci Resolve."""
import sys

OUT_DIR = sys.argv[1]
MAX_WORDS = 12

# Default custom curves. In = critically damped spring fit, Out = ease-in (accelerate away).
IN_LUT = "[0] = { 0, RH = { 0.275, 0.325 } },\n\t\t\t\t\t\t\t[1] = { 1, LH = { 0.175, 1 } }"
OUT_LUT = "[0] = { 0, RH = { 0.4, 0 } },\n\t\t\t\t\t\t\t[1] = { 1, LH = { 1, 1 } }"
# Word title defaults, tuned by hand on the C2a timeline.
WORDS_IN_LUT = ("[0] = { 0, RH = { 0.213646252453327, 0.252491025626659 } },\n\t\t\t\t\t\t\t"
                "[0.571506936300528] = { 0.910587139749722, LH = { 0.20095504447351, 0.716230347657587 }, RH = { 0.677919976375094, 0.96640144690031 } },\n\t\t\t\t\t\t\t"
                "[1] = { 1, LH = { 0.815938757359981, 1 } }")
WORDS_OUT_LUT = ("[0.0053475935828875] = { 0.0148148148148146, RH = { 0.278990164710916, 0.0148148148148146 } },\n\t\t\t\t\t\t\t"
                 "[0.622914464189847] = { 0.585685903685503, LH = { 0.586668586937423, 0.315474304017224 }, RH = { 0.678248481491738, 0.998188372535311 } },\n\t\t\t\t\t\t\t"
                 "[1] = { 1, LH = { 1, 1 } }")
WORDS_FONT = ("Garet", "Book")


def lut(name, keys):
    return f"""\t\t\t\t{name} = LUTBezier {{
\t\t\t\t\tKeyColorSplines = {{
\t\t\t\t\t\t[0] = {{
\t\t\t\t\t\t\t{keys}
\t\t\t\t\t\t}}
\t\t\t\t\t}},
\t\t\t\t\tSplineColor = {{ Red = 255, Green = 255, Blue = 255 }},
\t\t\t\t}},
"""


def curve(name, lookup, input_expr, curve_type="Custom", ease_in="Sine", ease_out="Sine", instance_of=None):
    if instance_of:
        return f"""\t\t\t\t{name} = LUTLookup {{
\t\t\t\t\tSourceOp = "{instance_of}",
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tSettingsNest = Input(),
\t\t\t\t\t\tInput = Input {{ Value = 0, Expression = "{input_expr}", }},
\t\t\t\t\t}},
\t\t\t\t}},
"""
    return f"""\t\t\t\t{name} = LUTLookup {{
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tNameSet = true,
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tSource = Input {{ Value = FuID {{ "Custom" }}, }},
\t\t\t\t\t\tInput = Input {{ Value = 0, Expression = "{input_expr}", }},
\t\t\t\t\t\tCurve = Input {{ Value = FuID {{ "{curve_type}" }}, }},
\t\t\t\t\t\tEaseIn = Input {{ Value = FuID {{ "{ease_in}" }}, }},
\t\t\t\t\t\tEaseOut = Input {{ Value = FuID {{ "{ease_out}" }}, }},
\t\t\t\t\t\tLookup = Input {{ SourceOp = "{lookup}", Source = "Value", }},
\t\t\t\t\t}},
\t\t\t\t}},
"""


def expr_mod(name, inputs, number="0", px="0", py="0"):
    ins = "".join(f"\t\t\t\t\t\t{k} = {v},\n" for k, v in inputs.items())
    return f"""\t\t\t\t{name} = Expression {{
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tNameSet = true,
\t\t\t\t\tInputs = {{
{ins}\t\t\t\t\t\tNumberExpression = Input {{ Value = "{number}", }},
\t\t\t\t\t\tPointExpressionX = Input {{ Value = "{px}", }},
\t\t\t\t\t\tPointExpressionY = Input {{ Value = "{py}", }},
\t\t\t\t\t}},
\t\t\t\t}},
"""


def slider(key, label, default, lo, hi, min_allowed=None):
    extra = f", INP_MinAllowed = {min_allowed}" if min_allowed is not None else ""
    return (f'\t\t\t\t\t\t{key} = {{ LINKS_Name = "{label}", LINKID_DataType = "Number", '
            f'INPID_InputControl = "SliderControl", INP_Default = {default}, INP_MinScale = {lo}, '
            f'INP_MaxScale = {hi}{extra}, ICS_ControlPage = "Controls" }},\n')


def text_inputs(text_src, text_name):
    """Group inspector controls for text look. text_src is where the typed text lives."""
    return f"""\t\t\t\tTextContent = InstanceInput {{ SourceOp = "{text_src[0]}", Source = "{text_src[1]}", Name = "Text", Page = "Controls" }},
\t\t\t\tFont = InstanceInput {{ SourceOp = "{text_name}", Source = "Font", ControlGroup = 2 }},
\t\t\t\tStyle = InstanceInput {{ SourceOp = "{text_name}", Source = "Style", ControlGroup = 2 }},
\t\t\t\tRed = InstanceInput {{ SourceOp = "{text_name}", Source = "Red1", Name = "Color", ControlGroup = 3, Default = 1 }},
\t\t\t\tGreen = InstanceInput {{ SourceOp = "{text_name}", Source = "Green1", ControlGroup = 3, Default = 1 }},
\t\t\t\tBlue = InstanceInput {{ SourceOp = "{text_name}", Source = "Blue1", ControlGroup = 3, Default = 1 }},
\t\t\t\tAlpha = InstanceInput {{ SourceOp = "{text_name}", Source = "Alpha1", ControlGroup = 3, Default = 1 }},
\t\t\t\tSize = InstanceInput {{ SourceOp = "{text_name}", Source = "Size", Default = 0.08, MinScale = 0.01, MaxScale = 0.3 }},
\t\t\t\tTracking = InstanceInput {{ SourceOp = "{text_name}", Source = "CharacterSpacing", Name = "Tracking", Default = 0.98, MinScale = 0.8, MaxScale = 1.4 }},
\t\t\t\tLineSpacing = InstanceInput {{ SourceOp = "{text_name}", Source = "LineSpacing", Name = "Line Spacing", Default = 0.95, MinScale = 0.5, MaxScale = 2 }},
\t\t\t\tPosition = InstanceInput {{ SourceOp = "{text_name}", Source = "Center", Name = "Position" }},
\t\t\t\tJustifyL = InstanceInput {{ SourceOp = "{text_name}", Source = "HorizontalLeftCenterRight", Name = "Justify", Default = 0 }},
"""


def curve_inputs(prefix, label, op):
    return f"""\t\t\t\t{prefix}Curve = InstanceInput {{ SourceOp = "{op}", Source = "Curve", Name = "{label} Curve" }},
\t\t\t\t{prefix}EaseIn = InstanceInput {{ SourceOp = "{op}", Source = "EaseIn", Width = 0.5 }},
\t\t\t\t{prefix}EaseOut = InstanceInput {{ SourceOp = "{op}", Source = "EaseOut", Width = 0.5 }},
\t\t\t\t{prefix}Lookup = InstanceInput {{ SourceOp = "{op}", Source = "Lookup", Name = "{label} Custom Curve", ControlGroup = {40 if prefix == "In" else 41} }},
"""


def text_plus(name, styled_text_line, extra="", font=("Helvetica Neue", "Medium")):
    return f"""\t\t\t\t{name} = TextPlus {{
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tNameSet = true,
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tGlobalOut = Input {{ Value = 20000, }},
\t\t\t\t\t\tWidth = Input {{ Value = 1920, }},
\t\t\t\t\t\tHeight = Input {{ Value = 1080, }},
\t\t\t\t\t\tUseFrameFormatSettings = Input {{ Value = 1, }},
\t\t\t\t\t\t["Gamut.SLogVersion"] = Input {{ Value = FuID {{ "SLog2" }}, }},
{styled_text_line}\t\t\t\t\t\tFont = Input {{ Value = "{font[0]}", }},
\t\t\t\t\t\tStyle = Input {{ Value = "{font[1]}", }},
\t\t\t\t\t\tSize = Input {{ Value = 0.08, }},
\t\t\t\t\t\tCharacterSpacing = Input {{ Value = 0.98, }},
\t\t\t\t\t\tLineSpacing = Input {{ Value = 0.95, }},
\t\t\t\t\t\tVerticalJustificationNew = Input {{ Value = 3, }},
\t\t\t\t\t\tHorizontalJustificationNew = Input {{ Value = 3, }},
{extra}\t\t\t\t\t\tManualFontKerningPlacement = Input {{
\t\t\t\t\t\t\tValue = StyledText {{ Array = {{ }}, Value = "" }},
\t\t\t\t\t\t}},
\t\t\t\t\t}},
\t\t\t\t}},
"""


def out_stage(ctrl, fg_op, out_lut=OUT_LUT):
    """Shared exit: whole title fades, blurs and lifts together, ending on the clip's last frame."""
    p = f"min(max((time-(comp.RenderEnd+1-{ctrl}.OutDur))/max({ctrl}.OutDur,1),0),1)"
    return (
        lut("OutCurveLookup", out_lut)
        + curve("OutCurve", "OutCurveLookup", p)
        + expr_mod("OutFx",
                   {"n1": 'Input { SourceOp = "OutCurve", Source = "Value", }',
                    "n2": f'Input {{ Value = 0.015, Expression = "{ctrl}.OutLift", }}'},
                   number="1-min(max(n1,0),1)", px="0.5", py="0.5+n2*n1")
        + f"""\t\t\t\tOutBlurTool = Blur {{
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tNameSet = true,
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tFilter = Input {{ Value = FuID {{ "Gaussian" }}, }},
\t\t\t\t\t\tXBlurSize = Input {{ Value = 0, Expression = "max(0, {ctrl}.OutBlur*(1-OutMerge.Blend))", }},
\t\t\t\t\t\tInput = Input {{ SourceOp = "{fg_op}", Source = "Output", }},
\t\t\t\t\t}},
\t\t\t\t}},
\t\t\t\tClear = Background {{
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tNameSet = true,
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tGlobalOut = Input {{ Value = 20000, }},
\t\t\t\t\t\tWidth = Input {{ Value = 1920, }},
\t\t\t\t\t\tHeight = Input {{ Value = 1080, }},
\t\t\t\t\t\tUseFrameFormatSettings = Input {{ Value = 1, }},
\t\t\t\t\t\t["Gamut.SLogVersion"] = Input {{ Value = FuID {{ "SLog2" }}, }},
\t\t\t\t\t\tTopLeftAlpha = Input {{ Value = 0, }},
\t\t\t\t\t}},
\t\t\t\t}},
\t\t\t\tOutMerge = Merge {{
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tNameSet = true,
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tBackground = Input {{ SourceOp = "Clear", Source = "Output", }},
\t\t\t\t\t\tForeground = Input {{ SourceOp = "OutBlurTool", Source = "Output", }},
\t\t\t\t\t\tCenter = Input {{ SourceOp = "OutFx", Source = "PointResult", }},
\t\t\t\t\t\tBlend = Input {{ SourceOp = "OutFx", Source = "NumberResult", }},
\t\t\t\t\t\tPerformDepthMerge = Input {{ Value = 0, }},
\t\t\t\t\t}},
\t\t\t\t}},
"""
    )


def wrap(group, inputs, tools):
    return f"""{{
\tTools = ordered() {{
\t\t{group} = GroupOperator {{
\t\t\tCtrlWZoom = false,
\t\t\tInputs = ordered() {{
{inputs}\t\t\t}},
\t\t\tOutputs = {{
\t\t\t\tMainOutput1 = InstanceOutput {{ SourceOp = "OutMerge", Source = "Output" }},
\t\t\t}},
\t\t\tViewInfo = GroupInfo {{ Pos = {{ 0, 0 }} }},
\t\t\tTools = ordered() {{
{tools}\t\t\t}},
\t\t}},
\t}},
\tActiveTool = "{group}",
}}
"""


# ---------------------------------------------------------------- letters (Follower)
def build_letters():
    c = "Fol"
    p = f"min(max(time/max({c}.InDur,1),0),1)"
    n1 = 'Input { SourceOp = "InCurve", Source = "Value", }'
    tools = (
        lut("InCurveLookup", IN_LUT)
        + curve("InCurve", "InCurveLookup", p)
        # The Follower time-shifts connected modifiers per letter, so these (and the curve they read) cascade.
        + expr_mod("EaseOpacity", {"n1": n1, "n2": f'Input {{ Value = 0.35, Expression = "{c}.Rise", }}'},
                   number="min(max(n1,0),1)", px="0", py="-n2*(1-n1)")
        + expr_mod("EaseBlur", {"n1": n1, "n2": f'Input {{ Value = 6, Expression = "{c}.InBlur", }}'},
                   number="max(0,n2*(1-n1))")
        + expr_mod("EaseScale", {"n1": n1, "n2": f'Input {{ Value = 0.96, Expression = "{c}.InScale", }}'},
                   number="n2+(1-n2)*n1")
        + f"""\t\t\t\tFol = StyledTextFollower {{
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tNameSet = true,
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tText = Input {{
\t\t\t\t\t\t\tValue = StyledText {{ Array = {{ }}, Value = "Type your title" }},
\t\t\t\t\t\t}},
\t\t\t\t\t\tDelay = Input {{ Value = 0.6, }},
\t\t\t\t\t\tTransform1 = Input {{ Value = 1, }},
\t\t\t\t\t\tInDur = Input {{ Value = 18, }},
\t\t\t\t\t\tRise = Input {{ Value = 0.35, }},
\t\t\t\t\t\tInBlur = Input {{ Value = 6, }},
\t\t\t\t\t\tInScale = Input {{ Value = 0.96, }},
\t\t\t\t\t\tOutDur = Input {{ Value = 12, }},
\t\t\t\t\t\tOutLift = Input {{ Value = 0.015, }},
\t\t\t\t\t\tOutBlur = Input {{ Value = 12, }},
\t\t\t\t\t\tOpacity1 = Input {{ SourceOp = "EaseOpacity", Source = "NumberResult", }},
\t\t\t\t\t\tOffset1 = Input {{ SourceOp = "EaseOpacity", Source = "PointResult", }},
\t\t\t\t\t\tSoftnessX1 = Input {{ SourceOp = "EaseBlur", Source = "NumberResult", }},
\t\t\t\t\t\tSoftnessY1 = Input {{ SourceOp = "EaseBlur", Source = "NumberResult", }},
\t\t\t\t\t\tSizeX1 = Input {{ SourceOp = "EaseScale", Source = "NumberResult", }},
\t\t\t\t\t\tSizeY1 = Input {{ SourceOp = "EaseScale", Source = "NumberResult", }},
\t\t\t\t\t}},
\t\t\t\t\tUserControls = ordered() {{
{slider("InDur", "In Duration (frames)", 18, 1, 60, 1)}{slider("Rise", "Rise Distance", 0.35, 0, 1.5)}{slider("InBlur", "In Blur", 6, 0, 30, 0)}{slider("InScale", "In Scale From", 0.96, 0.5, 1.2)}{slider("OutDur", "Out Duration (frames)", 12, 0, 60, 0)}{slider("OutLift", "Out Lift", 0.015, 0, 0.1)}{slider("OutBlur", "Out Blur", 12, 0, 40, 0)}\t\t\t\t\t}},
\t\t\t\t}},
"""
        + text_plus("Txt", '\t\t\t\t\t\tStyledText = Input { SourceOp = "Fol", Source = "StyledText", },\n')
        + out_stage(c, "Txt")
    )
    inputs = (
        text_inputs(("Fol", "Text"), "Txt")
        + f"""\t\t\t\tInDur = InstanceInput {{ SourceOp = "Fol", Source = "InDur", Default = 18 }},
\t\t\t\tStagger = InstanceInput {{ SourceOp = "Fol", Source = "Delay", Name = "Stagger (frames / letter)", Default = 0.6, MinScale = 0, MaxScale = 6 }},
\t\t\t\tOrder = InstanceInput {{ SourceOp = "Fol", Source = "Order" }},
"""
        + curve_inputs("In", "In", "InCurve")
        + """\t\t\t\tRise = InstanceInput { SourceOp = "Fol", Source = "Rise", Default = 0.35 },
\t\t\t\tInBlur = InstanceInput { SourceOp = "Fol", Source = "InBlur", Default = 6 },
\t\t\t\tInScale = InstanceInput { SourceOp = "Fol", Source = "InScale", Default = 0.96 },
\t\t\t\tOutDur = InstanceInput { SourceOp = "Fol", Source = "OutDur", Default = 12 },
"""
        + curve_inputs("Out", "Out", "OutCurve")
        + """\t\t\t\tOutLift = InstanceInput { SourceOp = "Fol", Source = "OutLift", Default = 0.015 },
\t\t\t\tOutBlur = InstanceInput { SourceOp = "Fol", Source = "OutBlur", Default = 12 },
"""
    )
    return wrap("FluidReveal", inputs, tools)


# ---------------------------------------------------------------- words (one Text+ instance per word)
S = "Txt1.StyledText.Value"
NCH = f"select(2, string.gsub({S}, '[^\\\\128-\\\\191]', ''))"  # character count (UTF-8 aware)


def word_bound(k, which):
    """Character offset of the start (which=3) or end (which=4) of word k, or nil if there is no word k."""
    return f"({{string.find({S}, '^%s*' .. string.rep('%S+%s+', {k - 1}) .. '()%S+()')}})[{which}]"


def chars_before(byte_expr, skip_newlines=False):
    cls = "\\\\n" if skip_newlines else ""
    return f"select(2, string.gsub(string.sub({S}, 1, ({byte_expr} or 1)-1), '[^\\\\128-\\\\191{cls}]', ''))"


def write_on(k, which, last):
    if last and which == 4:
        return "1"
    b = word_bound(k, which)
    # Text+ write-on numbers letters without line breaks but counts them in the total, so a
    # word's start skips line breaks while its end and the total include them (verified by render).
    # Pad each word's range by a third of a letter (into the surrounding space) so float rounding
    # can never drop its first or last letter. No word k -> exactly empty range at the end of the text.
    pad = "-0.3" if which == 3 else "+0.3"
    return f"({b} and ({chars_before(b, skip_newlines=(which == 3))}{pad}) or {NCH})/math.max({NCH},1)"


def hook_word_inputs(k, start, c="Main"):
    """Hook preset: per-word highlight driven by Main.Hi{k} (0 off, 1 highlight, 2 slam).
    Colour and outline (extra weight without changing the layout) switch to the accent colour
    held on Main's TopLeft colour; the word pops from a larger size and settles around its own
    centre (Text+ word transform), so the other words never move."""
    hi = f"{c}.Hi{k}"
    pop = (f"1+{hi}*{c}.PopAmount*(1-min(max((time-({start}))/max({c}.PopDur,1),0),1))^2")
    rows = [f'Red1 = Input {{ Value = 1, Expression = "{hi} > 0 and {c}.TopLeftRed or Txt1.Red1", }}',
            f'Green1 = Input {{ Value = 1, Expression = "{hi} > 0 and {c}.TopLeftGreen or Txt1.Green1", }}',
            f'Blue1 = Input {{ Value = 1, Expression = "{hi} > 0 and {c}.TopLeftBlue or Txt1.Blue1", }}',
            f'Enabled2 = Input {{ Value = 0, Expression = "{hi} > 0 and 1 or 0", }}',
            f'Thickness2 = Input {{ Value = 0, Expression = "{c}.HiWeight", }}',
            'Size2 = Input { Value = 1, }',                     # Resolve leaves a script-enabled element at size 0
            'SizeX2 = Input { Value = 1, }',
            'SizeY2 = Input { Value = 1, }',
            f'Red2 = Input {{ Value = 1, Expression = "{c}.TopLeftRed", }}',
            f'Green2 = Input {{ Value = 1, Expression = "{c}.TopLeftGreen", }}',
            f'Blue2 = Input {{ Value = 1, Expression = "{c}.TopLeftBlue", }}',
            f'WordSizeX = Input {{ Value = 1, Expression = "{pop}", }}',
            f'WordSizeY = Input {{ Value = 1, Expression = "{pop}", }}']
    return "".join(f"\t\t\t\t\t\t{r},\n" for r in rows)


def kinetic_word_inputs(k, start, c="Main"):
    """Kinetic (CapCut-style) preset: each word springs in (about 70% -> 110% -> 100%), the word
    being spoken lights up in the accent colour (karaoke), and key words (Hi{k} 1, slam 2) stay
    coloured and slightly bigger. Outline and shadow come from the Txt1 template."""
    hi = f"{c}.Hi{k}"
    nxt = (f"({c}.WordTime{k + 1} >= 0 and ({c}.WordTime{k + 1}+{c}.SyncOffset) or 100000)"
           if k < MAX_WORDS else "100000")
    on = f"({hi} > 0 or ({c}.Karaoke > 0.5 and time >= ({start}) and time < {nxt}))"
    pp = f"math.max((time-({start}))/math.max({c}.PopDur,1),0)"
    size = f"(1-{c}.Bounce*(1+0.5*{hi})*math.exp(-3.5*{pp})*math.cos(9*{pp}))*(1+{hi}*{c}.KeyHold)"
    rows = [f'Red1 = Input {{ Value = 1, Expression = "{on} and {c}.TopLeftRed or Txt1.Red1", }}',
            f'Green1 = Input {{ Value = 1, Expression = "{on} and {c}.TopLeftGreen or Txt1.Green1", }}',
            f'Blue1 = Input {{ Value = 1, Expression = "{on} and {c}.TopLeftBlue or Txt1.Blue1", }}',
            f'WordSizeX = Input {{ Value = 1, Expression = "{size}", }}',
            f'WordSizeY = Input {{ Value = 1, Expression = "{size}", }}']
    return "".join(f"\t\t\t\t\t\t{r},\n" for r in rows)


# Kinetic template look: dark outline (element 2) and soft drop shadow (element 3) on every word.
# Elements switched on by script start at size 0, so their sizes are set explicitly.
KINETIC_TEMPLATE = "".join(f"\t\t\t\t\t\t{r},\n" for r in [
    'Size = Input { Value = 0.075, }',
    'CharacterSpacing = Input { Value = 1, }',   # word positions are typeset at tracking 1.0
    'Enabled2 = Input { Value = 0, Expression = "Main.Outline > 0 and 1 or 0", }',
    'Size2 = Input { Value = 1, }', 'SizeX2 = Input { Value = 1, }', 'SizeY2 = Input { Value = 1, }',
    'Thickness2 = Input { Value = 0.06, Expression = "Main.Outline", }',
    'Red2 = Input { Value = 0, }', 'Green2 = Input { Value = 0, }', 'Blue2 = Input { Value = 0, }',
    'Enabled3 = Input { Value = 1, }', 'Size3 = Input { Value = 1, }', 'SizeX3 = Input { Value = 1, }', 'SizeY3 = Input { Value = 1, }',
    'Red3 = Input { Value = 0, }', 'Green3 = Input { Value = 0, }', 'Blue3 = Input { Value = 0, }',
    'Alpha3 = Input { Value = 0.6, Expression = "Main.ShadowAlpha", }',
    'Offset3 = Input { Value = { 0.004, -0.012 }, }',
    'SoftnessX3 = Input { Value = 4, Expression = "Main.ShadowSoft", }',
    'SoftnessY3 = Input { Value = 4, Expression = "Main.ShadowSoft", }',
])


def build_words(hook=False, kinetic=False):
    c = "Main"
    tools = lut("InCurveLookup", WORDS_IN_LUT)
    merges_prev = "Clear"
    templated = hook or kinetic
    if templated:
        # Txt1 is only the style template here (not rendered): every word, including the first,
        # is an instance, so a highlighted word can override its colour without touching the base.
        sample = "Is your business keeping up?" if kinetic else "It makes it MORE important."
        tools += text_plus("Txt1", f'\t\t\t\t\t\tStyledText = Input {{ Value = "{sample}", }},\n',
                           KINETIC_TEMPLATE if kinetic else "", ("Libre Baskerville", "Regular") if kinetic else WORDS_FONT)
    for k in range(1, MAX_WORDS + 1):
        last = k == MAX_WORDS
        # Word k starts at its spoken frame (WordTimeK, set by Auto Subtitles) or, when that is
        # -1, at an even stagger. SyncOffset nudges every word earlier (-) or later (+).
        start = f"({c}.WordTime{k} >= 0 and {c}.WordTime{k} or {k - 1}*{c}.WordStagger)+{c}.SyncOffset"
        p = f"min(max((time-({start}))/max({c}.InDur,1),0),1)"
        cname = f"InCurve{k}"
        if k == 1:
            tools += curve("InCurve1", "InCurveLookup", p)
        else:
            tools += curve(cname, None, p, instance_of="InCurve1")
        if kinetic:
            # Clean reveal: each word fades in over SnapIn frames with an ease-out cubic, rising a
            # touch and un-blurring (InBlur) as it settles. Bounce > 0 adds the spring pop back.
            tools += expr_mod(f"WordFx{k}",
                              {"n1": f'Input {{ Value = 0, Expression = "1-(1-min(max((time-({start}))/max({c}.SnapIn,1),0),1))^3", }}',
                               "n2": f'Input {{ Value = 0, Expression = "{c}.Rise", }}'},
                              number="n1", px="0.5", py="0.5-n2*(1-n1)")
        elif hook:
            # Highlighted words snap in faster (and so lose their blur sooner) while they pop.
            tools += expr_mod(f"WordFx{k}",
                              {"n1": f'Input {{ SourceOp = "{cname}", Source = "Value", }}',
                               "n2": f'Input {{ Value = 0.02, Expression = "{c}.Rise", }}',
                               "n3": f'Input {{ Value = 0, Expression = "{c}.Hi{k} > 0 and {c}.HiSnap or 0", }}'},
                              number="min(max(n1*(1+n3),0),1)", px="0.5", py="0.5-n2*(1-min(max(n1*(1+n3),0),1))")
        else:
            tools += expr_mod(f"WordFx{k}",
                              {"n1": f'Input {{ SourceOp = "{cname}", Source = "Value", }}',
                               "n2": f'Input {{ Value = 0.02, Expression = "{c}.Rise", }}'},
                              number="min(max(n1,0),1)", px="0.5", py="0.5-n2*(1-n1)")
        wo = (f'\t\t\t\t\t\tStart = Input {{ Value = 0, Expression = "{write_on(k, 3, last)}", }},\n'
              f'\t\t\t\t\t\tEnd = Input {{ Value = 1, Expression = "{write_on(k, 4, last)}", }},\n')
        layer = f"W{k}" if templated else f"Txt{k}"
        if kinetic:
            # Typeset per word: the build sets each layer's own word, style (Regular / Italic key
            # word) and centre from the font's real advances, so mixed styles never collide.
            wo = ('\t\t\t\t\t\tStyledText = Input { Value = "", },\n'
                  '\t\t\t\t\t\tStyle = Input { Value = "Regular", },\n'
                  '\t\t\t\t\t\tCenter = Input { Value = { 0.5, 0.5 }, },\n') + kinetic_word_inputs(k, start, c)
        elif hook:
            wo += hook_word_inputs(k, start, c)
        if k == 1 and not templated:
            tools += text_plus("Txt1", '\t\t\t\t\t\tStyledText = Input { Value = "Search is changing.", },\n', wo, WORDS_FONT)
        else:
            tools += f"""\t\t\t\t{layer} = TextPlus {{
\t\t\t\t\tSourceOp = "Txt1",
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tSettingsNest = Input(),
{wo}\t\t\t\t\t}},
\t\t\t\t}},
"""
        tools += f"""\t\t\t\tWordBlur{k} = Blur {{
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tNameSet = true,
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tFilter = Input {{ Value = FuID {{ "Gaussian" }}, }},
\t\t\t\t\t\tXBlurSize = Input {{ Value = 0, Expression = "max(0, {c}.InBlur*(1-WordMerge{k}.Blend))", }},
\t\t\t\t\t\tInput = Input {{ SourceOp = "{layer}", Source = "Output", }},
\t\t\t\t\t}},
\t\t\t\t}},
\t\t\t\tWordMerge{k} = Merge {{
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tNameSet = true,
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tBackground = Input {{ SourceOp = "{merges_prev}", Source = "Output", }},
\t\t\t\t\t\tForeground = Input {{ SourceOp = "WordBlur{k}", Source = "Output", }},
\t\t\t\t\t\tCenter = Input {{ SourceOp = "WordFx{k}", Source = "PointResult", }},
\t\t\t\t\t\tBlend = Input {{ SourceOp = "WordFx{k}", Source = "NumberResult", }},
\t\t\t\t\t\tPerformDepthMerge = Input {{ Value = 0, }},
\t\t\t\t\t}},
\t\t\t\t}},
"""
        merges_prev = f"WordMerge{k}"
    word_time_inputs = "".join(f"\t\t\t\t\t\tWordTime{k} = Input {{ Value = -1, }},\n" for k in range(1, MAX_WORDS + 1))
    word_time_controls = "".join(
        f'\t\t\t\t\t\tWordTime{k} = {{ LINKS_Name = "Word {k} Time (frames, -1 = auto)", LINKID_DataType = "Number", '
        f'INPID_InputControl = "SliderControl", INP_Default = -1, INP_MinScale = -1, INP_MaxScale = 120, INP_MinAllowed = -1, '
        f'IC_Visible = false, ICS_ControlPage = "Controls" }},\n' for k in range(1, MAX_WORDS + 1))
    if hook:
        # Accent = Main's own TopLeft colour (warm highlighter yellow by default).
        word_time_inputs += ("\t\t\t\t\t\tTopLeftRed = Input { Value = 1, },\n\t\t\t\t\t\tTopLeftGreen = Input { Value = 0.82, },\n"
                             "\t\t\t\t\t\tTopLeftBlue = Input { Value = 0.25, },\n\t\t\t\t\t\tPopAmount = Input { Value = 0.10, },\n"
                             "\t\t\t\t\t\tPopDur = Input { Value = 6, },\n\t\t\t\t\t\tHiWeight = Input { Value = 0.02, },\n"
                             "\t\t\t\t\t\tHiSnap = Input { Value = 1.5, },\n")
        word_time_inputs += "".join(f"\t\t\t\t\t\tHi{k} = Input {{ Value = 0, }},\n" for k in range(1, MAX_WORDS + 1))
        word_time_controls += (slider("PopAmount", "Highlight Pop (extra size at reveal)", 0.10, 0, 0.6, 0)
                               + slider("PopDur", "Highlight Pop Settle (frames)", 6, 1, 30, 1)
                               + slider("HiWeight", "Highlight Weight (outline)", 0.02, 0, 0.1, 0)
                               + slider("HiSnap", "Highlight Snap (faster reveal)", 1.5, 0, 4, 0))
        word_time_controls += "".join(
            f'\t\t\t\t\t\tHi{k} = {{ LINKS_Name = "Highlight Word {k} (0 off, 1 on, 2 slam)", LINKID_DataType = "Number", '
            f'INPID_InputControl = "SliderControl", INP_Default = 0, INP_MinScale = 0, INP_MaxScale = 2, INP_MinAllowed = 0, '
            f'INP_MaxAllowed = 2, INP_Integer = true, ICS_ControlPage = "Controls" }},\n' for k in range(1, MAX_WORDS + 1))
    if kinetic:
        kin = [("Karaoke", "Light Up Spoken Word (0/1)", 0, 0, 1), ("Bounce", "Bounce Pop (0 = clean fade)", 0, 0, 0.6),
               ("PopDur", "Bounce Length (frames)", 10, 1, 30), ("KeyHold", "Key Word Extra Size", 0, 0, 0.3),
               ("SnapIn", "Fade In (frames)", 8, 1, 24), ("Outline", "Outline Thickness", 0, 0, 0.2),
               ("ShadowAlpha", "Shadow Opacity", 0.5, 0, 1), ("ShadowSoft", "Shadow Softness", 6, 0, 20)]
        # Key-word colour defaults to white: the italic is the highlight (Tim's reference look).
        word_time_inputs += ("\t\t\t\t\t\tTopLeftRed = Input { Value = 1, },\n\t\t\t\t\t\tTopLeftGreen = Input { Value = 1, },\n"
                             "\t\t\t\t\t\tTopLeftBlue = Input { Value = 1, },\n")
        word_time_inputs += "".join(f"\t\t\t\t\t\t{key} = Input {{ Value = {d}, }},\n" for key, _, d, _, _ in kin)
        # Chunks swap cleanly (no outro); words rise 1% of frame height and clear a light blur
        # (later keys win in the table).
        word_time_inputs += ("\t\t\t\t\t\tOutDur = Input { Value = 0, },\n\t\t\t\t\t\tRise = Input { Value = 0.01, },\n"
                             "\t\t\t\t\t\tInBlur = Input { Value = 6, },\n\t\t\t\t\t\tOutBlur = Input { Value = 0, },\n"
                             "\t\t\t\t\t\tOutLift = Input { Value = 0, },\n")
        word_time_inputs += "".join(f"\t\t\t\t\t\tHi{k} = Input {{ Value = 0, }},\n" for k in range(1, MAX_WORDS + 1))
        word_time_controls += "".join(slider(key, label, d, lo, hi_, lo) for key, label, d, lo, hi_ in kin)
        word_time_controls += "".join(
            f'\t\t\t\t\t\tHi{k} = {{ LINKS_Name = "Key Word {k} (0 off, 1 key, 2 slam)", LINKID_DataType = "Number", '
            f'INPID_InputControl = "SliderControl", INP_Default = 0, INP_MinScale = 0, INP_MaxScale = 2, INP_MinAllowed = 0, '
            f'INP_MaxAllowed = 2, INP_Integer = true, ICS_ControlPage = "Controls" }},\n' for k in range(1, MAX_WORDS + 1))
    # Unconnected node that only holds the animation sliders the expressions read.
    tools += f"""\t\t\t\tMain = Background {{
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tNameSet = true,
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tWidth = Input {{ Value = 16, }},
\t\t\t\t\t\tHeight = Input {{ Value = 16, }},
\t\t\t\t\t\tWordStagger = Input {{ Value = 4, }},
\t\t\t\t\t\tSyncOffset = Input {{ Value = -2, }},
\t\t\t\t\t\tInDur = Input {{ Value = 18, }},
\t\t\t\t\t\tRise = Input {{ Value = 0.02, }},
\t\t\t\t\t\tInBlur = Input {{ Value = 10, }},
\t\t\t\t\t\tOutDur = Input {{ Value = 12, }},
\t\t\t\t\t\tOutLift = Input {{ Value = 0.015, }},
\t\t\t\t\t\tOutBlur = Input {{ Value = 12, }},
{word_time_inputs}\t\t\t\t\t}},
\t\t\t\t\tUserControls = ordered() {{
{slider("WordStagger", "Stagger (frames / word, when not synced)", 4, 0, 15, 0)}{slider("SyncOffset", "Sync Offset (frames)", -2, -10, 10)}{slider("InDur", "In Duration (frames)", 18, 1, 60, 1)}{slider("Rise", "Rise Distance", 0.02, 0, 0.1)}{slider("InBlur", "In Blur", 10, 0, 40, 0)}{slider("OutDur", "Out Duration (frames)", 12, 0, 60, 0)}{slider("OutLift", "Out Lift", 0.015, 0, 0.1)}{slider("OutBlur", "Out Blur", 12, 0, 40, 0)}{word_time_controls}\t\t\t\t\t}},
\t\t\t\t}},
"""
    tools += out_stage(c, merges_prev, WORDS_OUT_LUT)
    inputs = (
        text_inputs(("Txt1", "StyledText"), "Txt1")
        + f"""\t\t\t\tInDur = InstanceInput {{ SourceOp = "{c}", Source = "InDur", Default = 18 }},
\t\t\t\tWordStagger = InstanceInput {{ SourceOp = "{c}", Source = "WordStagger", Default = 4 }},
\t\t\t\tSyncOffset = InstanceInput {{ SourceOp = "{c}", Source = "SyncOffset", Default = -2 }},
"""
        + curve_inputs("In", "In", "InCurve1")
        + f"""\t\t\t\tRise = InstanceInput {{ SourceOp = "{c}", Source = "Rise", Default = 0.02 }},
\t\t\t\tInBlur = InstanceInput {{ SourceOp = "{c}", Source = "InBlur", Default = 10 }},
\t\t\t\tOutDur = InstanceInput {{ SourceOp = "{c}", Source = "OutDur", Default = 12 }},
"""
        + curve_inputs("Out", "Out", "OutCurve")
        + f"""\t\t\t\tOutLift = InstanceInput {{ SourceOp = "{c}", Source = "OutLift", Default = 0.015 }},
\t\t\t\tOutBlur = InstanceInput {{ SourceOp = "{c}", Source = "OutBlur", Default = 12 }},
"""
    )
    if hook:
        inputs += (f'\t\t\t\tHiRed = InstanceInput {{ SourceOp = "{c}", Source = "TopLeftRed", Name = "Highlight Color", ControlGroup = 7, Default = 1, Page = "Highlight" }},\n'
                   f'\t\t\t\tHiGreen = InstanceInput {{ SourceOp = "{c}", Source = "TopLeftGreen", ControlGroup = 7, Default = 0.82, Page = "Highlight" }},\n'
                   f'\t\t\t\tHiBlue = InstanceInput {{ SourceOp = "{c}", Source = "TopLeftBlue", ControlGroup = 7, Default = 0.25, Page = "Highlight" }},\n'
                   f'\t\t\t\tPopAmount = InstanceInput {{ SourceOp = "{c}", Source = "PopAmount", Default = 0.10, Page = "Highlight" }},\n'
                   f'\t\t\t\tPopDur = InstanceInput {{ SourceOp = "{c}", Source = "PopDur", Default = 6, Page = "Highlight" }},\n'
                   f'\t\t\t\tHiWeight = InstanceInput {{ SourceOp = "{c}", Source = "HiWeight", Default = 0.02, Page = "Highlight" }},\n'
                   f'\t\t\t\tHiSnap = InstanceInput {{ SourceOp = "{c}", Source = "HiSnap", Default = 1.5, Page = "Highlight" }},\n')
        inputs += "".join(f'\t\t\t\tHi{k} = InstanceInput {{ SourceOp = "{c}", Source = "Hi{k}", Default = 0, Page = "Highlight" }},\n'
                          for k in range(1, MAX_WORDS + 1))
    if kinetic:
        inputs += (f'\t\t\t\tHiRed = InstanceInput {{ SourceOp = "{c}", Source = "TopLeftRed", Name = "Highlight Color", ControlGroup = 7, Default = 1, Page = "Kinetic" }},\n'
                   f'\t\t\t\tHiGreen = InstanceInput {{ SourceOp = "{c}", Source = "TopLeftGreen", ControlGroup = 7, Default = 1, Page = "Kinetic" }},\n'
                   f'\t\t\t\tHiBlue = InstanceInput {{ SourceOp = "{c}", Source = "TopLeftBlue", ControlGroup = 7, Default = 1, Page = "Kinetic" }},\n')
        inputs += "".join(f'\t\t\t\t{key} = InstanceInput {{ SourceOp = "{c}", Source = "{key}", Default = {d}, Page = "Kinetic" }},\n'
                          for key, _, d, _, _ in kin)
        inputs += "".join(f'\t\t\t\tHi{k} = InstanceInput {{ SourceOp = "{c}", Source = "Hi{k}", Default = 0, Page = "Kinetic" }},\n'
                          for k in range(1, MAX_WORDS + 1))
    return wrap("FluidRevealWords", inputs, tools)


# ---------------------------------------------------------------- name title (Beon Name Title)
def build_name():
    """Two-line name super: big Garet Book name over a small letter-spaced Garet Book role line.
    Same clean reveal as the Kinetic captions (ease-out fade, small rise, blur clearing), the role
    line following the name by Stagger frames, and the shared fade-out on the clip's last frames."""
    c = "Ctl"
    shadow = "".join(f"\t\t\t\t\t\t{r},\n" for r in [
        f'Enabled3 = Input {{ Value = 0, Expression = "{c}.ShadowAlpha > 0 and 1 or 0", }}', 'Size3 = Input { Value = 1, }', 'SizeX3 = Input { Value = 1, }', 'SizeY3 = Input { Value = 1, }',
        'Red3 = Input { Value = 0, }', 'Green3 = Input { Value = 0, }', 'Blue3 = Input { Value = 0, }',
        f'Alpha3 = Input {{ Value = 0.5, Expression = "{c}.ShadowAlpha", }}', 'Offset3 = Input { Value = { 0.004, -0.012 }, }',
        f'SoftnessX3 = Input {{ Value = 6, Expression = "{c}.ShadowSoft", }}', f'SoftnessY3 = Input {{ Value = 6, Expression = "{c}.ShadowSoft", }}'])
    name = ('\t\t\t\t\t\tStyledText = Input { Value = "Bonnie", },\n')
    role = ('\t\t\t\t\t\tStyledText = Input { Value = "FOUNDER & CEO", },\n')
    tools = text_plus("Name", name, shadow + "\t\t\t\t\t\tCenter = Input { Value = { 0.68, 0.6 }, },\n"
                      "\t\t\t\t\t\tHorizontalLeftCenterRight = Input { Value = -1, },\n", ("Garet", "Book"))
    tools = tools.replace("Size = Input { Value = 0.08, }", "Size = Input { Value = 0.11, }")
    r = text_plus("Role", role, shadow + f'\t\t\t\t\t\tCenter = Input {{ Value = {{ 0.68, 0.52 }}, Expression = "Point(Name.Center.X, Name.Center.Y-{c}.Gap)", }},\n'
                  '\t\t\t\t\t\tHorizontalLeftCenterRight = Input { Value = -1, Expression = "Name.HorizontalLeftCenterRight", }\n'.rstrip("\n") + ",\n"
                  '\t\t\t\t\t\tAlpha1 = Input { Value = 0.85, }\n'.rstrip("\n") + ",\n", ("Garet", "Book"))
    tools += r.replace("Size = Input { Value = 0.08, }", "Size = Input { Value = 0.026, }").replace(
        "CharacterSpacing = Input { Value = 0.98, }", "CharacterSpacing = Input { Value = 1.18, }")
    prev = "Clear"
    for line, delay in (("Name", "0"), ("Role", f"{c}.Stagger")):
        p = f"1-(1-min(max((time-{delay})/max({c}.InDur,1),0),1))^3"
        tools += expr_mod(f"{line}Fx", {"n1": f'Input {{ Value = 0, Expression = "{p}", }}',
                                         "n2": f'Input {{ Value = 0.012, Expression = "{c}.Rise", }}'},
                          number="n1", px="0.5", py="0.5-n2*(1-n1)")
        tools += f"""\t\t\t\t{line}Blur = Blur {{
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tNameSet = true,
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tFilter = Input {{ Value = FuID {{ "Gaussian" }}, }},
\t\t\t\t\t\tXBlurSize = Input {{ Value = 0, Expression = "max(0, {c}.InBlur*(1-{line}Merge.Blend))", }},
\t\t\t\t\t\tInput = Input {{ SourceOp = "{line}", Source = "Output", }},
\t\t\t\t\t}},
\t\t\t\t}},
\t\t\t\t{line}Merge = Merge {{
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tNameSet = true,
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tBackground = Input {{ SourceOp = "{prev}", Source = "Output", }},
\t\t\t\t\t\tForeground = Input {{ SourceOp = "{line}Blur", Source = "Output", }},
\t\t\t\t\t\tCenter = Input {{ SourceOp = "{line}Fx", Source = "PointResult", }},
\t\t\t\t\t\tBlend = Input {{ SourceOp = "{line}Fx", Source = "NumberResult", }},
\t\t\t\t\t\tPerformDepthMerge = Input {{ Value = 0, }},
\t\t\t\t\t}},
\t\t\t\t}},
"""
        prev = f"{line}Merge"
    ctl = [("InDur", "In Duration (frames)", 10, 1, 40), ("Stagger", "Role Delay (frames)", 6, 0, 30),
           ("Rise", "Rise Distance", 0.012, 0, 0.1), ("InBlur", "In Blur", 8, 0, 40),
           ("OutDur", "Out Duration (frames)", 10, 0, 40), ("OutLift", "Out Lift", 0.01, 0, 0.1),
           ("OutBlur", "Out Blur", 10, 0, 40), ("Gap", "Line Gap", 0.085, 0, 0.3),
           ("ShadowAlpha", "Shadow Opacity (0 = off)", 0, 0, 1), ("ShadowSoft", "Shadow Softness", 6, 0, 20)]
    tools += f"""\t\t\t\t{c} = Background {{
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tNameSet = true,
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tWidth = Input {{ Value = 16, }},
\t\t\t\t\t\tHeight = Input {{ Value = 16, }},
""" + "".join(f"\t\t\t\t\t\t{k} = Input {{ Value = {d}, }},\n" for k, _, d, _, _ in ctl) + """\t\t\t\t\t},
\t\t\t\t\tUserControls = ordered() {
""" + "".join(slider(k, label, d, lo, hi_, lo) for k, label, d, lo, hi_ in ctl) + """\t\t\t\t\t},
\t\t\t\t},
"""
    tools += out_stage(c, prev)
    inputs = (
        '\t\t\t\tNameText = InstanceInput { SourceOp = "Name", Source = "StyledText", Name = "Name", Page = "Controls" },\n'
        '\t\t\t\tRoleText = InstanceInput { SourceOp = "Role", Source = "StyledText", Name = "Role", Page = "Controls" },\n'
        '\t\t\t\tPosition = InstanceInput { SourceOp = "Name", Source = "Center", Name = "Position" },\n'
        '\t\t\t\tJustify = InstanceInput { SourceOp = "Name", Source = "HorizontalLeftCenterRight", Name = "Justify", Default = -1 },\n'
        '\t\t\t\tNameFont = InstanceInput { SourceOp = "Name", Source = "Font", Name = "Name Font", ControlGroup = 2 },\n'
        '\t\t\t\tNameStyle = InstanceInput { SourceOp = "Name", Source = "Style", ControlGroup = 2 },\n'
        '\t\t\t\tNameSize = InstanceInput { SourceOp = "Name", Source = "Size", Name = "Name Size", Default = 0.11 },\n'
        '\t\t\t\tRoleFont = InstanceInput { SourceOp = "Role", Source = "Font", Name = "Role Font", ControlGroup = 3 },\n'
        '\t\t\t\tRoleStyle = InstanceInput { SourceOp = "Role", Source = "Style", ControlGroup = 3 },\n'
        '\t\t\t\tRoleSize = InstanceInput { SourceOp = "Role", Source = "Size", Name = "Role Size", Default = 0.026 },\n'
        '\t\t\t\tRoleTracking = InstanceInput { SourceOp = "Role", Source = "CharacterSpacing", Name = "Role Tracking", Default = 1.18 },\n'
        '\t\t\t\tRoleOpacity = InstanceInput { SourceOp = "Role", Source = "Alpha1", Name = "Role Opacity", Default = 0.85 },\n'
        + "".join(f'\t\t\t\t{k} = InstanceInput {{ SourceOp = "{c}", Source = "{k}", Default = {d} }},\n' for k, _, d, _, _ in ctl))
    return wrap("BeonNameTitle", inputs, tools)


open(f"{OUT_DIR}/Fluid Reveal.setting", "w").write(build_letters())
open(f"{OUT_DIR}/Fluid Reveal Words.setting", "w").write(build_words())
open(f"{OUT_DIR}/Fluid Reveal Words Hook.setting", "w").write(build_words(hook=True))
open(f"{OUT_DIR}/Fluid Reveal Words Kinetic.setting", "w").write(build_words(kinetic=True))
open(f"{OUT_DIR}/Beon Name Title.setting", "w").write(build_name())
print("ok")
