
INTENT greeting: "问候和欢迎"
INTENT product_query: "产品咨询" 
INTENT order_status: "订单状态查询"
INTENT complaint: "投诉建议"

RULE greeting_rule
WHEN INTENT_IS greeting
THEN
    RESPOND "您好！欢迎来到XX电商客服中心。"
    RESPOND "请问有什么可以帮您？"

RULE product_rule  
WHEN INTENT_IS product_query
THEN
    RESPOND "感谢您对我们产品的关注！"
    RESPOND "请告诉我您想了解哪类产品？我们有电子产品、家居用品等多个品类。"

RULE order_rule
WHEN INTENT_IS order_status
THEN
    RESPOND "我来帮您查询订单状态。"
    RESPOND "请提供您的订单号，或者您也可以在APP中查看最新物流信息。"

RULE complaint_rule
WHEN INTENT_IS complaint
THEN
    RESPOND "抱歉给您带来不便！"
    RESPOND "请详细描述您遇到的问题，我们会尽快处理。"

RULE default_rule
WHEN INTENT_IS unknown
THEN
    RESPOND "抱歉，我没有理解您的问题。"
    RESPOND "请您重新描述，或联系人工客服。"