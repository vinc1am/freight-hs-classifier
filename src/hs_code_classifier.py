import os
import requests
import base64

def classify_commodity(cargo_desc, hs_code_list, gpt4v_key, gpt4v_endpoint):

    headers = {
        "Content-Type": "application/json",
        "api-key": gpt4v_key,
    }
    payload = {
        "messages": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": f"""
    You are the freight cargo commodity classifier to select the best-matched HS Code from the provided list.
    
    HS Code List:
    {hs_code_list}
    
    You ONLY could select the top 3 result. Also you must at least choose 1 from the hs code list even the information is not sufficient.
    Please return below format as [(<top 1 hs4>, <rationale of select this hs code>), (<second hs4>, <rationale of select this hs code>), ...].
    Result Example:
    [("8450", "The Samsung Pro Max is a smartphone, which falls under the category of 'Telephone sets, including smartphones and other telephones for cellular networks or for other wireless networks.'),..."]
    """
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cargo_desc
                    }
                ]
            }
        ],
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 800
    }

    response = requests.post(gpt4v_endpoint, headers=headers, json=payload).json()

    return response['choices'][0]['message']['content']



