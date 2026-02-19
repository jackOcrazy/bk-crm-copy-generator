import json
import os
from openai import OpenAI

# Cargar Brand Pack
with open("brand_packs/bk_brand_pack.json", "r", encoding="utf-8") as f:
    brand_pack = json.load(f)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_bk_copy(
    country,
    channel,
    campaign_type,
    campaign_name="",
    product="",
    price="",
    objective="promo",
    n=5
):
    brand = brand_pack["brand"]
    tone = ", ".join(brand_pack["tone"])
    vocab = ", ".join(brand_pack["food_vocabulary"])
    expressions = ", ".join(brand_pack["crm_expressions"])
    emojis = " ".join(brand_pack["allowed_emojis"])

    channel_rules = brand_pack["channels"][channel]
    regional = brand_pack["regional_adaptation"][country]

    prompt = f"""
You are a CRM copywriter for {brand} in {country}.

Brand tone: {tone}
Vocabulary: {vocab}
Expressions: {expressions}
Allowed emojis: {emojis}

Regional style: {regional['style']}, energy {regional['energy']}

Channel: {channel}
Rules: {channel_rules}

Campaign type: {campaign_type}
Campaign name: {campaign_name}
Product: {product}
Price: {price}
Objective: {objective}

Generate {n} CRM copy options following brand voice and channel rules.
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
        objective="promo"
    )

    print(result)
