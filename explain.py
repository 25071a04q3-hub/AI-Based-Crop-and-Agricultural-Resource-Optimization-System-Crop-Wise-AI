def generate_crop_explanation(
    crop_name: str,
    suitability_prob: float,
    yield_info: dict,
    input_dict: dict,
    lang: str = "English"
) -> str:
    """
    Generates plain-language driver explanation for a given crop recommendation.
    """
    n, p, k = input_dict.get('N', 0), input_dict.get('P', 0), input_dict.get('K', 0)
    rain = input_dict.get('rainfall', 0)
    temp = input_dict.get('temperature', 0)
    ph = input_dict.get('ph', 0)

    reasons = []
    if rain > 150 and crop_name in ['rice', 'jute', 'coconut', 'papaya']:
        reasons.append("high rainfall conditions support water-intensive growth")
    elif rain < 70 and crop_name in ['chickpea', 'mothbeans', 'mungbean', 'muskmelon']:
        reasons.append("drought tolerance fits low rainfall levels")

    if ph >= 6.0 and ph <= 7.5:
        reasons.append("optimal soil pH level")

    if n > 80 and crop_name in ['cotton', 'maize', 'banana', 'watermelon']:
        reasons.append("rich nitrogen availability enhances foliage")

    if not reasons:
        reasons.append("balanced soil nutrient and weather compatibility")

    reason_str = ", ".join(reasons)

    if lang == "Telugu":
        return f"**{crop_name.upper()}**: అనుకూలత {suitability_prob*100:.1f}%. కారణాలు: {reason_str}. అంచనా దిగుబడి: {yield_info['expected']} t/ha (పరిధి: {yield_info['low']} - {yield_info['high']} t/ha)."
    elif lang == "Hindi":
        return f"**{crop_name.upper()}**: उपयुक्तता {suitability_prob*100:.1f}%. कारण: {reason_str}। अनुमानित उपज: {yield_info['expected']} t/ha (सीमा: {yield_info['low']} - {yield_info['high']} t/ha) ।"
    else:
        return f"**{crop_name.upper()}** (Suitability: {suitability_prob*100:.1f}%): Recommended because {reason_str}. Expected yield is **{yield_info['expected']} t/ha** (range: {yield_info['low']} - {yield_info['high']} t/ha)."