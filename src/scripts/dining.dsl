INTENT greeting: "打招呼或开始预订"
INTENT booking_query: "餐饮预订需求"
INTENT confirm: "确认预订"
INTENT cancel: "取消预订"
INTENT fallback: "无法理解的输入"

RULE start_greeting
WHEN INTENT_IS greeting
THEN
RESPOND_KB "greeting_intro"
SET_STAGE "category_select"

RULE set_dining_category
WHEN INTENT_IS booking_query
AND USER_MENTION_ANY "订餐|预订|餐厅|餐饮"
THEN
RESPOND_KB "category_confirm_dining"
SET_VAR current_category = "餐饮"
ADD_TO_CHAIN "category" "餐饮"
SET_STAGE "brand_select"
RESPOND_KB "brand_select_prompt"
SUGGEST_BRANDS

RULE suggest_restaurants
WHEN INTENT_IS booking_query
AND CONTEXT_STAGE_IS "brand_select"
THEN
RESPOND_KB "brand_select_prompt"
SUGGEST_BRANDS

RULE brand_known_series_select
WHEN INTENT_IS booking_query
AND CONTEXT_STAGE_IS "brand_select"
AND CONTEXT_HAS "current_brand"
THEN
SET_STAGE "series_select"
RESPOND_KB "series_select_prompt"
SUGGEST_SERIES

RULE series_prompt_on_series_select
WHEN INTENT_IS booking_query
AND CONTEXT_STAGE_IS "series_select"
AND CONTEXT_HAS "current_brand"
THEN
RESPOND_KB "series_select_prompt"
SUGGEST_SERIES

RULE series_known_config_select
WHEN INTENT_IS booking_query
AND CONTEXT_STAGE_IS "series_select"
AND CONTEXT_HAS "current_series"
THEN
SET_STAGE "config_select"
RESPOND_KB "config_select_prompt"
DESCRIBE_SERIES_CONFIG
RESPOND_KB "party_size_prompt"
SET_STAGE "details_collect"

RULE confirm_after_timeslot
WHEN INTENT_IS confirm
AND CONTEXT_STAGE_IS "config_select"
THEN
RESPOND_KB "party_size_prompt"
SET_STAGE "details_collect"

RULE details_to_date
WHEN INTENT_IS booking_query
AND CONTEXT_STAGE_IS "details_collect"
AND CONTEXT_HAS "private_room"
THEN
SUGGEST_DATES
SET_STAGE "date_collect"

RULE date_to_budget
WHEN INTENT_IS booking_query
AND CONTEXT_STAGE_IS "date_collect"
THEN
RESPOND_KB "budget_prompt"
SET_STAGE "budget_collect"

RULE date_to_budget_confirm
WHEN INTENT_IS confirm
AND CONTEXT_STAGE_IS "date_collect"
THEN
RESPOND_KB "budget_prompt"
SET_STAGE "budget_collect"

RULE budget_to_contact
WHEN INTENT_IS booking_query
AND CONTEXT_STAGE_IS "budget_collect"
THEN
RESPOND_KB "contact_prompt"
SET_STAGE "contact_collect"

RULE budget_to_contact_confirm
WHEN INTENT_IS confirm
AND CONTEXT_STAGE_IS "budget_collect"
THEN
RESPOND_KB "contact_prompt"
SET_STAGE "contact_collect"

RULE summary_on_contact
WHEN INTENT_IS booking_query
AND CONTEXT_STAGE_IS "contact_collect"
THEN
RESPOND_KB "booking_summary_prompt"
SET_STAGE "final_confirm"

RULE summary_on_contact_confirm
WHEN INTENT_IS confirm
AND CONTEXT_STAGE_IS "contact_collect"
THEN
RESPOND_KB "booking_summary_prompt"
SET_STAGE "final_confirm"

RULE finalize_confirm
WHEN INTENT_IS confirm
AND CONTEXT_STAGE_IS "final_confirm"
THEN
RESPOND "✅ 预订已确认！我们稍后与您联系完成锁定。"
RESPOND "👋 感谢您使用餐饮预订助手，期待为您服务！"
RESPOND "🍽️ 祝您用餐愉快！"
SET_STAGE "completed"

RULE finalize_cancel
WHEN INTENT_IS cancel
AND CONTEXT_STAGE_IS "final_confirm"
THEN
RESPOND "已取消预订，您可以随时重新开始。"
SET_STAGE "category_select"

RULE finalize_continue
WHEN INTENT_IS booking_query
AND CONTEXT_STAGE_IS "final_confirm"
THEN
RESPOND "好的，我们继续调整，您可以更改餐厅、套餐或时间。"
SET_STAGE "brand_select"

RULE confirm_booking
WHEN INTENT_IS confirm
AND CONTEXT_STAGE_IS "config_select"
THEN
RESPOND "已为您记录该时段，稍后为您确认座位。"
SET_STAGE "completed"

RULE fallback_category
WHEN INTENT_IS fallback
AND CONTEXT_STAGE_IS "category_select"
THEN
RESPOND_KB "ask_category_first"

RULE fallback_restart
WHEN INTENT_IS fallback
AND CONTEXT_STAGE_IS "welcome"
THEN
RESPOND_KB "restart_prompt_short"
SET_STAGE "category_select"

RULE fallback_details_collect
WHEN INTENT_IS fallback
AND CONTEXT_STAGE_IS "details_collect"
THEN
RESPOND_KB "private_room_prompt"

RULE fallback_date_collect
WHEN INTENT_IS fallback
AND CONTEXT_STAGE_IS "date_collect"
THEN
RESPOND_KB "date_prompt"

RULE fallback_budget_collect
WHEN INTENT_IS fallback
AND CONTEXT_STAGE_IS "budget_collect"
THEN
RESPOND_KB "budget_prompt"

RULE fallback_contact_collect
WHEN INTENT_IS fallback
AND CONTEXT_STAGE_IS "contact_collect"
THEN
RESPOND_KB "contact_prompt"

RULE fallback_completed
WHEN INTENT_IS fallback
AND CONTEXT_STAGE_IS "completed"
THEN
RESPOND "👋 您的预订已完成，如需重新预订，请说'订餐'或'重新开始'。"