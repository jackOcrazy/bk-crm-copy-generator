import streamlit as st
import json
import re
from openai import OpenAI

# =========================
# LOAD BRAND PACK
# =========================
with open("brand_packs/bk_brand_pack.json", "r", encoding="utf-8") as f:
    brand_pack = json.load(f)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# =========================
# REGIONAL STYLE
# =========================
def regional_flavor(country):
    if country == "Argentina":
        return """
Use Argentine Spanish with voseo (probá, pedí, vení).
Energetic and expressive tone.
Avoid Spain Spanish.
"""
    else:
        return """
Use Chilean Spanish.
Direct promo tone.
"""

# =========================
# SEGMENT INTENT
# =========================
def segment_intent(segment):
    intents = {
        "Reactivación": "User inactive >9 weeks. Bring back with craving/nostalgia.",
        "Churned": "User cooling (5–9 weeks). Trigger return.",
        "New": "Registered but never ordered. First purchase.",
        "Retained": "Active last 4 weeks. Maintain frequency."
    }
    return intents.get(segment, "")

# =========================
# CHANNEL FORMAT RULES
# =========================
def channel_format(channel):
    if channel == "push":
        return """
Format:
Title (max 30 characters)
Body (max 130 characters)
No CTA.
"""
    elif channel == "inapp":
        return """
Format:
Title (max 5 words)
Body (max 15 words)
CTA
"""
    elif channel == "slideup":
        return """
Format:
Title (max 15 words)
CTA (max 3 words)
No body.
"""

def channel_fields(channel):
    if channel == "push":
        return {"title": True, "body": True, "cta": False}
    if channel == "inapp":
        return {"title": True, "body": True, "cta": True}
    if channel == "slideup":
        return {"title": True, "body": False, "cta": True}
    return {"title": True, "body": True, "cta": True}

# =========================
# COPY GENERATION
# =========================
def generate_bk_copy(country, channel, campaign_type, campaign_context, product, price, segment=None, n=3):
    brand = brand_pack["brand"]
    tone = ", ".join(brand_pack["tone"])
    vocab = ", ".join(brand_pack["food_vocabulary"])
    expressions = ", ".join(brand_pack["crm_expressions"])
    emojis = " ".join(brand_pack["allowed_emojis"])

    region_style = regional_flavor(country)
    format_rules = channel_format(channel)

    product_text = f"Product: {product}" if product else ""
    price_text = f"Price: {price}" if price else ""

    theme_block = ""
    if campaign_context and campaign_context.strip():
        theme_block = f"""
Campaign theme: {campaign_context}
Make it feel like Burger King x {campaign_context}.
"""

    # =========================
    # MULTI SEGMENT MODE (2 options per segment)
    # =========================
    if segment == "Todos":
        segments = ["Reactivación", "Churned", "New", "Retained"]

        seg_prompt = ""
        for seg in segments:
            intent = segment_intent(seg)
            seg_prompt += f"""
SEGMENT: {seg}
CRM objective: {intent}
Write TWO distinct copy options for this lifecycle stage.
"""

        prompt = f"""
You are a CRM copywriter for {brand} in {country}.

{region_style}

Brand tone: {tone}
Vocabulary: {vocab}
Expressions: {expressions}
Allowed emojis: {emojis}

Channel: {channel}
Channel rules (STRICT):
{format_rules}

Campaign type: {campaign_type}
{theme_block}

{product_text}
{price_text}

Generate TWO (2) copy options for EACH segment below, following the channel format strictly.

{seg_prompt}

Output EXACT format:

Segment: Reactivación
Option 1:
Title:
Body:
CTA:
Option 2:
Title:
Body:
CTA:

Segment: Churned
Option 1:
Title:
Body:
CTA:
Option 2:
Title:
Body:
CTA:

Segment: New
Option 1:
Title:
Body:
CTA:
Option 2:
Title:
Body:
CTA:

Segment: Retained
Option 1:
Title:
Body:
CTA:
Option 2:
Title:
Body:
CTA:

Important:
- If channel is push: do NOT include CTA lines (omit them).
- If channel is slideup: do NOT include Body lines (omit them).
- If channel is inapp: include Title, Body, CTA.
"""
    else:
        # =========================
        # SINGLE SEGMENT MODE (3 options)
        # =========================
        segment_block = ""
        if segment and segment != "Todos":
            intent = segment_intent(segment)
            segment_block = f"""
User segment: {segment}
CRM objective: {intent}
Adapt tone and persuasion to lifecycle stage.
"""

        prompt = f"""
You are a CRM copywriter for {brand} in {country}.

{region_style}

Brand tone: {tone}
Vocabulary: {vocab}
Expressions: {expressions}
Allowed emojis: {emojis}

{segment_block}

Channel: {channel}
Channel rules (STRICT):
{format_rules}

Campaign type: {campaign_type}
{theme_block}

{product_text}
{price_text}

Write EXACTLY {n} copy options.

Output rules:
- Start each option with "Option 1:", "Option 2:", "Option 3:"
- Use labels exactly: Title:, Body:, CTA:
- If channel is push: do NOT include CTA lines.
- If channel is slideup: do NOT include Body lines. CTA max 3 words.
- If channel is inapp: include Title, Body, CTA.
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    return response.output_text

# =========================
# HELPERS & PARSERS
# =========================
def _extract_line(block: str, label: str):
    m = re.search(rf"{label}:\s*(.*)", block, flags=re.IGNORECASE)
    return m.group(1).strip() if m else ""

def parse_options(text: str):
    pattern = r"(Option\s+[123]:)(.*?)(?=(Option\s+[123]:)|\Z)"
    matches = re.findall(pattern, text, flags=re.DOTALL | re.IGNORECASE)

    options = []
    for m in matches:
        block = (m[0] + m[1]).strip()
        options.append({
            "title": _extract_line(block, "Title"),
            "body": _extract_line(block, "Body"),
            "cta": _extract_line(block, "CTA"),
            "raw": block
        })

    if not options:
        options = [{"title": "", "body": "", "cta": "", "raw": text.strip()}]

    return options

def parse_segment_options(text: str):
    """
    Expected structure:
    Segment: X
      Option 1:
        Title:
        Body:
        CTA:
      Option 2:
        ...
    """
    segments = ["Reactivación", "Churned", "New", "Retained"]
    results = {}

    for seg in segments:
        seg_pattern = rf"Segment:\s*{re.escape(seg)}.*?(?=Segment:|\Z)"
        seg_match = re.search(seg_pattern, text, flags=re.DOTALL | re.IGNORECASE)
        if not seg_match:
            continue

        seg_block = seg_match.group(0)

        # Extract Option 1 block
        opt1_match = re.search(r"Option\s*1:\s*(.*?)(?=Option\s*2:|\Z)", seg_block, flags=re.DOTALL | re.IGNORECASE)
        opt2_match = re.search(r"Option\s*2:\s*(.*?)(?=\Z)", seg_block, flags=re.DOTALL | re.IGNORECASE)

        def parse_opt(opt_text):
            return {
                "title": _extract_line(opt_text, "Title"),
                "body": _extract_line(opt_text, "Body"),
                "cta": _extract_line(opt_text, "CTA"),
                "raw": opt_text.strip()
            }

        opt1 = parse_opt(opt1_match.group(1)) if opt1_match else {"title": "", "body": "", "cta": "", "raw": ""}
        opt2 = parse_opt(opt2_match.group(1)) if opt2_match else {"title": "", "body": "", "cta": "", "raw": ""}

        results[seg] = [opt1, opt2]

    return results

# =========================
# STREAMLIT UI
# =========================
st.set_page_config(page_title="BK CRM Copy Generator", page_icon="🍔")
st.title("🍔 BK CRM Copy Generator")

country = st.selectbox("País", ["Chile", "Argentina"])
channel = st.selectbox("Canal", ["push", "inapp", "slideup"])

# Keep individual selection always available ✅
segment = st.selectbox(
    "Segmento usuario",
    ["Todos", "Reactivación", "Churned", "New", "Retained"]
)

campaign_type = st.selectbox(
    "Tipo campaña",
    [
        "Promo producto",
        "Lanzamiento producto",
        "Descuento / precio especial",
        "Combo / bundle",
        "Estreno serie/película",
        "Colaboración / licencia",
        "Fecha especial",
        "Seasonal (temporal)",
        "Tráfico app",
        "Engagement",
        "Branding",
        "Always-on"
    ]
)

campaign_context = st.text_input("Contexto campaña (ej: Stranger Things, Navidad, Welcome to Derry, 2x1 combos)")
product = st.text_input("Producto (opcional)", "")
price = st.text_input("Precio (opcional)", "")

if st.button("Generar copys"):
    with st.spinner("Generando..."):
        result = generate_bk_copy(
            country,
            channel,
            campaign_type,
            campaign_context,
            product,
            price,
            segment=segment,
            n=3
        )

    st.subheader("Resultados")
    fields = channel_fields(channel)

    if segment == "Todos":
        segs = parse_segment_options(result)

        if not segs:
            st.warning("No se pudo parsear por segmentos. Mira la salida raw abajo.")
        else:
            for seg, opts in segs.items():
                with st.container(border=True):
                    st.markdown(f"## {seg}")
                    for idx, opt in enumerate(opts, start=1):
                        st.markdown(f"### Opción {idx}")
                        if fields["title"] and opt["title"]:
                            st.markdown(f"**Title:** {opt['title']}")
                        if fields["body"] and opt["body"]:
                            st.markdown(f"**Body:** {opt['body']}")
                        if fields["cta"] and opt["cta"]:
                            st.markdown(f"**CTA:** {opt['cta']}")
    else:
        options = parse_options(result)
        for i, opt in enumerate(options, start=1):
            with st.container(border=True):
                st.markdown(f"### Opción {i}")
                if fields["title"] and opt["title"]:
                    st.markdown(f"**Title:** {opt['title']}")
                if fields["body"] and opt["body"]:
                    st.markdown(f"**Body:** {opt['body']}")
                if fields["cta"] and opt["cta"]:
                    st.markdown(f"**CTA:** {opt['cta']}")
                if not (opt["title"] or opt["body"] or opt["cta"]):
                    st.text(opt["raw"])

    with st.expander("Ver salida completa (raw)"):
        st.text(result)
