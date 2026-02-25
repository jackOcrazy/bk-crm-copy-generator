import json
import os
from openai import OpenAI

# Cargar Brand Pack
with open("brand_packs/bk_brand_pack.json", "r", encoding="utf-8") as f:
    brand_pack = json.load(f)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
# SEGMENT INTENT
# =========================
def segment_intent(segment):
    if segment == "Reactivación":
        return "User inactive >9 weeks. Goal: bring back with craving and nostalgia."
    if segment == "Churned":
        return "User cooling (5–9 weeks). Goal: remind value and trigger return."
    if segment == "New":
        return "Registered but never ordered. Goal: first purchase motivation."
    if segment == "Retained":
        return "Active last 4 weeks. Goal: maintain frequency and loyalty."
    return ""

# =========================
# GENERATE COPY
# =========================
def generate_bk_copy(
    country,
    channel,
    campaign_type,
    campaign_name="",
    product="",
    price="",
    objective="promo",
    segment=None,
    n=5
):
    brand = brand_pack["brand"]
    tone = ", ".join(brand_pack["tone"])
    vocab = ", ".join(brand_pack["food_vocabulary"])
    expressions = ", ".join(brand_pack["crm_expressions"])
    emojis = " ".join(brand_pack["allowed_emojis"])

    channel_rules = brand_pack["channels"][channel]
    regional = brand_pack["regional_adaptation"][country]

    # Segment block
    segment_block = ""
    if segment:
        intent = segment_intent(segment)
        segment_block = f"""
User segment: {segment}

CRM objective:
{intent}

Adapt tone and persuasion to this lifecycle stage.
"""

    prompt = f"""
You are a CRM copywriter for {brand} in {country}.

Brand tone: {tone}
Vocabulary: {vocab}
Expressions: {expressions}
Allowed emojis: {emojis}

Regional style: {regional['style']}, energy {regional['energy']}

Channel: {channel}
Rules: {channel_rules}

{segment_block}

Campaign type: {campaign_type}
Campaign name: {campaign_name}
Product: {product}
Price: {price}
Objective: {objective}

Generate {n} CRM copy options following brand voice, channel rules and lifecycle intent.
Return each option on a new line.
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    return response.output_text


if __name__ == "__main__":
    result = generate_bk_copy(
        country="Chile",
        channel="push",
        campaign_type="promo",
        product="Combo Crispy",
        price="$4.990",
        objective="promo",
        segment="Reactivación"
    )

    print(result)
