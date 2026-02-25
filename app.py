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

    # Optional fields
    product_text = f"Product: {product}" if product else ""
    price_text = f"Price: {price}" if price else ""

    theme_block = ""
    if campaign_context and campaign_context.strip():
        theme_block = f"""
Campaign theme: {campaign_context}
Make it feel like Burger King x {campaign_context}.
"""

    # =========================
    # MULTI SEGMENT MODE
    # =========================
    if segment == "Todos" and channel == "push":
        segments = ["Reactivación", "Churned", "New", "Retained"]

        seg_prompt = ""
        for seg in segments:
            intent = segment_intent(seg)
            seg_prompt += f"""
SEGMENT: {seg}
CRM objective: {intent}
Write copy adapted to this lifecycle stage.
"""

        prompt = f"""
You are a CRM copywriter for {brand} in {country}.

{region_style}

Brand tone: {tone}
Vocabulary: {vocab}
Expressions: {expressions}
Allowed emojis: {emojis}

Channel: {channel}
Rules: {format_rules}

Campaign type: {campaign_type}
{theme_block}

{product_text}
{price_text}

Generate push copy for EACH segment below.

{seg_prompt}

Output EXACT format:

Segment: Reactivación
Title:
Body:

Segment: Churned
Title:
Body:

Segment: New
Title:
Body:

Segment: Retained
Title:
Body:
"""
    else:
        # SINGLE SEGMENT
        segment_block = ""
        if segment:
            intent = segment_intent(segment)
            segment_block = f"""
User segment: {segment}
CRM objective: {intent}
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
Rules: {format_rules}

Campaign type: {campaign_type}
{theme_block}

{product_text}
{price_text}

Write EXACTLY {n} copy options.

Format each:
Option 1:
Title:
Body:

Option 2:
Title:
Body:

Option 3:
Title:
Body:
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    return response.output_text

# =========================
# PARSER NORMAL OPTIONS
# =========================
def parse_options(text):
    pattern = r"Option\s+[123]:.*?(?=Option\s+[123]:|$)"
    matches = re.findall(pattern, text, re.DOTALL)

    options = []
    for m in matches:
        title = re.search(r"Title:\s*(.*)", m)
        body = re.search(r"Body:\s*(.*)", m)
        cta = re.search(r"CTA:\s*(.*)", m)

        options.append({
            "title": title.group(1).strip() if title else "",
            "body": body.group(1).strip() if body else "",
            "cta": cta.group(1).strip() if cta else "",
        })

    return options

# =========================
# PARSER SEGMENTS
# =========================
def parse_segments(text):
    segments = ["Reactivación", "Churned", "New", "Retained"]
    results = {}

    for seg in segments:
        pattern = rf"Segment:\s*{seg}.*?(?=Segment:|$)"
        match = re.search(pattern, text, re.DOTALL)

        if match:
            block = match.group(0)
            title = re.search(r"Title:\s*(.*)", block)
            body = re.search(r"Body:\s*(.*)", block)

            results[seg] = {
                "title": title.group(1).strip() if title else "",
                "body": body.group(1).strip() if body else "",
            }

    return results

# =========================
# STREAMLIT UI
# =========================
st.set_page_config(page_title="BK CRM Copy Generator", page_icon="🍔")
st.title("🍔 BK CRM Copy Generator")

country = st.selectbox("País", ["Chile", "Argentina"])
channel = st.selectbox("Canal", ["push", "inapp", "slideup"])

segment = None
if channel == "push":
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
        "Seasonal",
        "Tráfico app",
        "Engagement",
        "Branding",
        "Always-on"
    ]
)

campaign_context = st.text_input("Contexto campaña")
product = st.text_input("Producto (opcional)")
price = st.text_input("Precio (opcional)")

if st.button("Generar copys"):
    with st.spinner("Generando..."):
        result = generate_bk_copy(
            country,
            channel,
            campaign_type,
            campaign_context,
            product,
            price,
            segment=segment
        )

    st.subheader("Resultados")

    # =========================
    # MULTI SEGMENT DISPLAY
    # =========================
    if segment == "Todos" and channel == "push":
        segs = parse_segments(result)

        for seg, data in segs.items():
            with st.container(border=True):
                st.markdown(f"### {seg}")
                st.markdown(f"**Title:** {data['title']}")
                st.markdown(f"**Body:** {data['body']}")
    else:
        options = parse_options(result)

        for i, opt in enumerate(options, start=1):
            with st.container(border=True):
                st.markdown(f"### Opción {i}")
                if opt["title"]:
                    st.markdown(f"**Title:** {opt['title']}")
                if opt["body"]:
                    st.markdown(f"**Body:** {opt['body']}")
                if opt["cta"]:
                    st.markdown(f"**CTA:** {opt['cta']}")
