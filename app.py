import streamlit as st
import json
import os
import re
from openai import OpenAI

# =========================
# LOAD BRAND PACK
# =========================
with open("brand_packs/bk_brand_pack.json", "r", encoding="utf-8") as f:
    brand_pack = json.load(f)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
# REGIONAL STYLE
# =========================
def regional_flavor(country):
    if country == "Argentina":
        return """
Use Argentine Spanish with voseo (probá, pedí, vení).
Sound energetic and expressive.
Avoid neutral/Spain Spanish forms (no "coge", no "vale", no "vosotros").
"""
    else:
        return """
Use Chilean Spanish.
Direct promo tone.
Avoid overly formal language.
"""

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
def generate_bk_copy(country, channel, campaign_type, campaign_context, product, price, n=3):
    brand = brand_pack["brand"]
    tone = ", ".join(brand_pack["tone"])
    vocab = ", ".join(brand_pack["food_vocabulary"])
    expressions = ", ".join(brand_pack["crm_expressions"])
    emojis = " ".join(brand_pack["allowed_emojis"])

    region_style = regional_flavor(country)
    format_rules = channel_format(channel)

    # Optional fields
    product_text = f"Product (optional): {product}" if product else "Product (optional): (none)"
    price_text = f"Price (optional): {price}" if price else "Price (optional): (none)"

    # Theme block that truly influences output
    theme_block = ""
    if campaign_context and campaign_context.strip():
        theme_block = f"""
Campaign theme/context: {campaign_context}

Creative direction (MANDATORY):
- The copy MUST clearly reflect this theme in mood, wording, references or atmosphere.
- Make it feel like a crossover: Burger King x {campaign_context}.
- Keep BK voice, but adapt to the theme genre (horror/fantasy/festive/etc.).
"""

    prompt = f"""
You are a senior CRM creative copywriter for {brand} in {country}.

{region_style}

Brand base tone: {tone}
Brand vocabulary: {vocab}
Brand expressions: {expressions}
Allowed emojis: {emojis}

Campaign type: {campaign_type}

{theme_block}

{product_text}
{price_text}

Write EXACTLY 3 copy options for channel: {channel}.
Follow STRICTLY the channel format rules:

{format_rules}

Output rules:
- Write each option separated by a blank line.
- Start each option with "Option 1:", "Option 2:", "Option 3:".
- Use the labels exactly: Title:, Body:, CTA:
- If channel is push: do NOT include CTA.
- If channel is slideup: do NOT include Body, and CTA must be max 3 words.
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    return response.output_text

# =========================
# PARSER (to show pretty cards)
# =========================
def parse_options(text: str):
    # Splits by "Option X:" blocks
    pattern = r"(Option\s+[123]:)(.*?)(?=(Option\s+[123]:)|\Z)"
    matches = re.findall(pattern, text, flags=re.DOTALL | re.IGNORECASE)

    options = []
    for m in matches:
        block = (m[0] + m[1]).strip()

        title = ""
        body = ""
        cta = ""

        t = re.search(r"Title:\s*(.*)", block, flags=re.IGNORECASE)
        b = re.search(r"Body:\s*(.*)", block, flags=re.IGNORECASE)
        c = re.search(r"CTA:\s*(.*)", block, flags=re.IGNORECASE)

        if t: title = t.group(1).strip()
        if b: body = b.group(1).strip()
        if c: cta = c.group(1).strip()

        options.append({"raw": block, "title": title, "body": body, "cta": cta})

    # fallback: if model didn't follow structure, show whole thing as one block
    if not options:
        options = [{"raw": text.strip(), "title": "", "body": "", "cta": ""}]

    return options

# =========================
# STREAMLIT UI
# =========================
st.set_page_config(page_title="BK CRM Copy Generator", page_icon="🍔")
st.title("🍔 BK CRM Copy Generator")

country = st.selectbox("País", ["Chile", "Argentina"])
channel = st.selectbox("Canal", ["push", "inapp", "slideup"])

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
    with st.spinner("Generando copys BK..."):
        result = generate_bk_copy(country, channel, campaign_type, campaign_context, product, price, n=3)

    st.subheader("Resultados")
    options = parse_options(result)

    # Show pretty cards for each option
    for i, opt in enumerate(options, start=1):
        with st.container(border=True):
            st.markdown(f"### Opción {i}")
            if opt["title"]:
                st.markdown(f"**Title:** {opt['title']}")
            if opt["body"]:
                st.markdown(f"**Body:** {opt['body']}")
            if opt["cta"]:
                st.markdown(f"**CTA:** {opt['cta']}")
            if not (opt["title"] or opt["body"] or opt["cta"]):
                st.text(opt["raw"])

    # Raw output (optional debug view)
    with st.expander("Ver salida completa (raw)"):
        st.text(result)