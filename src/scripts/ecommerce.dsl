INTENT greeting: "问候和欢迎"
INTENT product_query: "产品咨询"
INTENT order_status: "订单状态查询"
INTENT complaint: "投诉建议"
INTENT cart_operation: "购物车操作"
INTENT confirmation: "确认性回答"  # 新增确认意图
INTENT fallback: "上下文兜底提示"
########################################
# 苹果专卖店
########################################

RULE greeting_rule
WHEN INTENT_IS greeting
THEN
    RESPOND_KB "greeting_intro"

########################################
# 全局重置和切换规则（高优先级）
########################################

# 从电脑切换到手机
RULE switch_computer_to_phone
WHEN INTENT_IS product_query
    AND USER_MENTION_ANY "手机|还是买手机|换成手机|改为手机|还是手机|买手机吧|手机吧"
    AND CONTEXT_EQ current_category = "电脑"
THEN
    RESET_SHOPPING_CONTEXT
    SET_VAR current_category = "手机"
    ADD_TO_CHAIN type = "category" value = "手机"
    SET_VAR current_brand = "苹果"
    ADD_TO_CHAIN type = "brand" value = "苹果"
    SET_STAGE "series_select"
    RESPOND_KB "switch_to_phone_done"
    SUGGEST_SERIES

# 从手机切换到电脑
RULE switch_phone_to_computer
WHEN INTENT_IS product_query
    AND USER_MENTION_ANY "电脑|还是买电脑|换成电脑|改为电脑"
    AND CONTEXT_EQ current_category = "手机"
THEN
    RESET_SHOPPING_CONTEXT
    SET_VAR current_category = "电脑"
    ADD_TO_CHAIN type = "category" value = "电脑"
    SET_STAGE "subtype_select"
    RESPOND_KB "switch_to_computer_prompt"

# 通用重置规则
RULE global_reset_rule
WHEN INTENT_IS product_query
    AND USER_MENTION_ANY "重新开始|重置|重新选|换一个|不要这个"
THEN
    RESET_SHOPPING_CONTEXT
    SET_STAGE "welcome"
    RESPOND_KB "global_reset_prompt"

########################################
# 非苹果品牌兜底处理：统一说明仅支持 Apple 产品
RULE product_query_non_apple_brand
WHEN INTENT_IS product_query
    AND USER_MENTION_ANY "联想|lenovo|戴尔|dell|华为|huawei|小米|红米|mi|oppo|vivo|荣耀|honor|三星|sony|索尼|惠普|hp|华硕|asus"
THEN
    RESPOND_KB "non_apple_brand_fallback"


# 第一步：明确大类（电脑/手机等）
########################################

# 电脑大类 - 增强：支持多种表达方式
RULE product_query_set_category_computer
WHEN INTENT_IS product_query
    AND USER_MENTION_ANY "电脑|计算机|笔记本|台式机|macbook|mac"
    AND CONTEXT_NOT_SET current_category
THEN
    SET_VAR current_category = "电脑"
    ADD_TO_CHAIN type = "category" value = "电脑"
    SET_STAGE "subtype_select"
    RESPOND_KB "computer_subtype_prompt"

# 手机大类 - 增强：支持多种表达方式
RULE product_query_set_category_phone
WHEN INTENT_IS product_query
    AND USER_MENTION_ANY "手机|iphone|华为|小米|三星|oppo|vivo"
    AND CONTEXT_NOT_SET current_category
THEN
    SET_VAR current_category = "手机"
    ADD_TO_CHAIN type = "category" value = "手机"
    SET_VAR current_brand = "苹果"
    ADD_TO_CHAIN type = "brand" value = "苹果"
    SET_STAGE "series_select"
    RESPOND_KB "phone_category_confirm"
    SUGGEST_SERIES

# iPad / 平板大类 - 直接进入苹果品牌的系列选择
RULE product_query_set_category_ipad
WHEN INTENT_IS product_query
    AND USER_MENTION_ANY "iPad|ipad|平板|平板电脑"
    AND CONTEXT_NOT_SET current_category
THEN
    SET_VAR current_category = "平板"
    ADD_TO_CHAIN type = "category" value = "平板"
    SET_VAR current_brand = "苹果"
    ADD_TO_CHAIN type = "brand" value = "苹果"
    SET_STAGE "series_select"
    RESPOND_KB "ipad_category_confirm"
    SUGGEST_SERIES


# 兜底：询问大类（根据 query_count 区分首次/重复）
RULE product_query_ask_category_first_time
WHEN INTENT_IS product_query
    AND CONTEXT_NOT_SET current_category
    AND CONTEXT_STAGE_IS "welcome"
    AND CONTEXT_HAS "query_count" = 0
THEN
    SET_STAGE "category_select"
    RESPOND_KB "ask_category_first"
    INCREMENT "query_count"

RULE product_query_ask_category_repeat
WHEN INTENT_IS product_query
    AND CONTEXT_NOT_SET current_category
    AND CONTEXT_STAGE_IS "category_select"
    AND CONTEXT_HAS "query_count"
THEN
    SET_STAGE "category_select"
    RESPOND_KB "ask_category_repeat"

########################################
# 第二步：电脑子类（笔记本/台式机）
########################################

# 子类选择由解释器快捷识别层处理（笔记本/台式机自动归类并切换到品牌选择阶段）

########################################
# 通用：基于知识库的品牌/系列动态推荐
########################################

# 品牌列表：基于当前品类的动态品牌推荐
RULE product_query_list_brands_dynamic
WHEN INTENT_IS product_query
    AND CONTEXT_STAGE_IS "brand_select"
    AND CONTEXT_HAS "current_category"
    AND USER_MENTION_ANY "有哪些品牌|推荐品牌|品牌有哪些"
THEN
    SUGGEST_BRANDS

# 系列列表：基于当前品类+品牌的动态系列/型号推荐
RULE product_query_list_series_dynamic
WHEN INTENT_IS product_query
    AND CONTEXT_STAGE_IS "series_select"
    AND CONTEXT_HAS "current_category"
    AND CONTEXT_HAS "current_brand"
    AND USER_MENTION_ANY "有哪些系列|推荐系列|推荐型号"
THEN
    SUGGEST_SERIES


########################################
# 第三步：笔记本品牌选择
########################################

# 直接指定品牌（跳过子类提问）
RULE product_query_direct_brand_apple
WHEN INTENT_IS product_query
     AND CONTEXT_EQ current_category = "电脑"
     AND CONTEXT_NOT_SET current_subtype
     AND CONTEXT_NOT_SET current_brand
     AND CONTEXT_STAGE_IS "subtype_select"
     AND USER_MENTION_ANY "苹果|apple|macbook|mac"
THEN
    SET_VAR current_subtype = "笔记本"
    ADD_TO_CHAIN type = "subtype" value = "笔记本"
    SET_VAR current_brand = "苹果"
    ADD_TO_CHAIN type = "brand" value = "苹果"
    SET_STAGE "series_select"
    SUGGEST_SERIES



# 苹果台式机品牌选择 - 针对“台式机”子类
RULE product_query_set_brand_apple_desktop
WHEN INTENT_IS product_query
    AND CONTEXT_EQ current_category = "电脑"
    AND CONTEXT_EQ current_subtype = "台式机"
    AND USER_MENTION_ANY "苹果|apple|imac|mac mini|mac studio|1|第一个"
    AND CONTEXT_NOT_SET current_brand
    AND CONTEXT_STAGE_IS "brand_select"
THEN
    SET_VAR current_brand = "苹果"
    ADD_TO_CHAIN type = "brand" value = "苹果"
    SET_STAGE "series_select"
    SUGGEST_SERIES

# 苹果笔记本 - 增强：支持多种表达和数字选择
RULE product_query_set_brand_apple_laptop
WHEN INTENT_IS product_query
     AND CONTEXT_EQ current_category = "电脑"
     AND CONTEXT_EQ current_subtype = "笔记本"
     AND USER_MENTION_ANY "苹果|apple|macbook|mac|air|macbook air|MacBook Air|1|第一个"
     AND CONTEXT_NOT_SET current_brand
     AND CONTEXT_NOT_SET current_series
     AND CONTEXT_STAGE_IS "brand_select"
THEN
    SET_VAR current_brand = "苹果"
    ADD_TO_CHAIN type = "brand" value = "苹果"
    SET_STAGE "series_select"
    SUGGEST_SERIES

RULE product_query_direct_series_air_from_brand_select
WHEN INTENT_IS product_query
    AND CONTEXT_EQ current_category = "电脑"
    AND CONTEXT_STAGE_IS "brand_select"
    AND USER_MENTION_ANY "air|Air|macbook air|MacBook Air"
    AND CONTEXT_NOT_SET current_series
THEN
    SET_VAR current_brand = "苹果"
    ADD_TO_CHAIN "brand" "苹果"
    SET_VAR current_series = "MacBook Air"
    ADD_TO_CHAIN "series" "MacBook Air"
    SET_STAGE "config_select"
    DESCRIBE_SERIES_CONFIG

RULE product_query_direct_series_pro_from_brand_select
WHEN INTENT_IS product_query
    AND CONTEXT_EQ current_category = "电脑"
    AND CONTEXT_STAGE_IS "brand_select"
    AND USER_MENTION_ANY "pro|Pro|macbook pro|MacBook Pro"
    AND CONTEXT_NOT_SET current_series
THEN
    SET_VAR current_brand = "苹果"
    ADD_TO_CHAIN "brand" "苹果"
    SET_VAR current_series = "MacBook Pro"
    ADD_TO_CHAIN "series" "MacBook Pro"
    SET_STAGE "config_select"
    DESCRIBE_SERIES_CONFIG


# iMac 系列选择
RULE product_query_set_series_imac
WHEN INTENT_IS product_query
    AND CONTEXT_EQ current_category = "电脑"
    AND CONTEXT_EQ current_brand = "苹果"
    AND CONTEXT_EQ current_subtype = "台式机"
    AND USER_MENTION_ANY "imac|iMac|3|第三个"
    AND CONTEXT_NOT_SET current_series
    AND CONTEXT_STAGE_IS "series_select"
THEN
    SET_VAR current_series = "iMac"
    ADD_TO_CHAIN type = "series" value = "iMac"
    SET_STAGE "config_select"
    DESCRIBE_SERIES_CONFIG


# iPad 系列选择 - 基于“平板”品类
RULE product_query_set_series_ipad_pro
WHEN INTENT_IS product_query
    AND CONTEXT_EQ current_category = "平板"
    AND CONTEXT_EQ current_brand = "苹果"
    AND USER_MENTION_ANY "ipad pro|iPad Pro|pro|1|第一个"
    AND CONTEXT_NOT_SET current_series
    AND CONTEXT_STAGE_IS "series_select"
THEN
    SET_VAR current_series = "iPad Pro"
    ADD_TO_CHAIN type = "series" value = "iPad Pro"
    SET_STAGE "config_select"
    DESCRIBE_SERIES_CONFIG

RULE product_query_set_series_ipad_air
WHEN INTENT_IS product_query
    AND CONTEXT_EQ current_category = "平板"
    AND CONTEXT_EQ current_brand = "苹果"
    AND USER_MENTION_ANY "ipad air|iPad Air|air|2|第二个"
    AND CONTEXT_NOT_SET current_series
    AND CONTEXT_STAGE_IS "series_select"
THEN
    SET_VAR current_series = "iPad Air"
    ADD_TO_CHAIN type = "series" value = "iPad Air"
    SET_STAGE "config_select"
    DESCRIBE_SERIES_CONFIG

RULE product_query_set_series_ipad
WHEN INTENT_IS product_query
    AND CONTEXT_EQ current_category = "平板"
    AND CONTEXT_EQ current_brand = "苹果"
    AND USER_MENTION_ANY "ipad|iPad|3|第三个"
    AND CONTEXT_NOT_SET current_series
    AND CONTEXT_STAGE_IS "series_select"
THEN
    SET_VAR current_series = "iPad"
    ADD_TO_CHAIN type = "series" value = "iPad"
    SET_STAGE "config_select"
    DESCRIBE_SERIES_CONFIG

RULE product_query_set_series_ipad_mini
WHEN INTENT_IS product_query
    AND CONTEXT_EQ current_category = "平板"
    AND CONTEXT_EQ current_brand = "苹果"
    AND USER_MENTION_ANY "ipad mini|iPad mini|mini|4|第四个"
    AND CONTEXT_NOT_SET current_series
    AND CONTEXT_STAGE_IS "series_select"
THEN
    SET_VAR current_series = "iPad mini"
    ADD_TO_CHAIN type = "series" value = "iPad mini"
    SET_STAGE "config_select"
    DESCRIBE_SERIES_CONFIG

# Mac mini 系列选择
RULE product_query_set_series_mac_mini
WHEN INTENT_IS product_query
    AND CONTEXT_EQ current_category = "电脑"
    AND CONTEXT_EQ current_brand = "苹果"
    AND CONTEXT_EQ current_subtype = "台式机"
    AND USER_MENTION_ANY "mac mini|mini|4|第四个"
    AND CONTEXT_NOT_SET current_series
    AND CONTEXT_STAGE_IS "series_select"
THEN
    SET_VAR current_series = "Mac mini"
    ADD_TO_CHAIN type = "series" value = "Mac mini"
    SET_STAGE "config_select"
    DESCRIBE_SERIES_CONFIG

# Mac Studio 系列选择
RULE product_query_set_series_mac_studio
WHEN INTENT_IS product_query
    AND CONTEXT_EQ current_category = "电脑"
    AND CONTEXT_EQ current_brand = "苹果"
    AND CONTEXT_EQ current_subtype = "台式机"
    AND USER_MENTION_ANY "mac studio|studio|5|第五个"
    AND CONTEXT_NOT_SET current_series
    AND CONTEXT_STAGE_IS "series_select"
THEN
    SET_VAR current_series = "Mac Studio"
    ADD_TO_CHAIN type = "series" value = "Mac Studio"
    SET_STAGE "config_select"
    DESCRIBE_SERIES_CONFIG


########################################
# 第四步：苹果笔记本系列选择
########################################

# MacBook Air - 增强：支持数字选择和多种名称
RULE product_query_set_series_air
WHEN INTENT_IS product_query
     AND CONTEXT_EQ current_category = "电脑"
     AND CONTEXT_EQ current_brand = "苹果"
     AND USER_MENTION_ANY "air|Air|1|第一个|选项一|macbook air"
     AND CONTEXT_NOT_SET current_series
     AND CONTEXT_STAGE_IS "series_select"
THEN
    SET_VAR current_series = "MacBook Air"
    ADD_TO_CHAIN type = "series" value = "MacBook Air"
    SET_STAGE "config_select"
    DESCRIBE_SERIES_CONFIG

# MacBook Pro - 增强：支持数字选择和多种名称
RULE product_query_set_series_pro
WHEN INTENT_IS product_query
     AND CONTEXT_EQ current_category = "电脑"
     AND CONTEXT_EQ current_brand = "苹果"
     AND USER_MENTION_ANY "pro|Pro|2|第二个|选项二|macbook pro"
     AND CONTEXT_NOT_SET current_series
     AND CONTEXT_STAGE_IS "series_select"
THEN
    SET_VAR current_series = "MacBook Pro"
    ADD_TO_CHAIN type = "series" value = "MacBook Pro"
    SET_STAGE "config_select"
    DESCRIBE_SERIES_CONFIG

# MacBook Pro with M3 (明确指定M3) - 增强：支持数字选择
RULE product_query_set_series_mbp_m3
WHEN INTENT_IS product_query
     AND CONTEXT_EQ current_category = "电脑"
     AND CONTEXT_EQ current_subtype = "笔记本"
     AND CONTEXT_EQ current_brand = "苹果"
     AND USER_MENTION_ANY "M3|m3|3|第三个|选项三"
     AND CONTEXT_NOT_SET current_series
     AND CONTEXT_STAGE_IS "series_select"
THEN
    SET_VAR current_series = "MacBook Pro M3"
    ADD_TO_CHAIN type = "series" value = "MacBook Pro with M3"
    SET_STAGE "size_select"
    RESPOND_KB "mbp_m3_size_options"

########################################
# 第五步：MacBook Air 尺寸选择
########################################

# Air 13寸 - 增强：支持数字选择和多种表达
RULE product_query_set_air_13
WHEN INTENT_IS product_query
     AND CONTEXT_EQ current_series = "MacBook Air"
     AND USER_MENTION_ANY "13|13.6|1|第一个|选项一|13寸"
     AND CONTEXT_STAGE_IS "config_select"
THEN
    SET_STAGE "storage_select"
    RESPOND_KB "air_13_storage_options"

# Air 15寸 - 增强：支持数字选择和多种表达
RULE product_query_set_air_15
WHEN INTENT_IS product_query
     AND CONTEXT_EQ current_series = "MacBook Air"
     AND USER_MENTION_ANY "15|15.3|2|第二个|15寸"
     AND CONTEXT_STAGE_IS "config_select"
THEN
    SET_STAGE "storage_select"
    RESPOND_KB "air_15_storage_options"

########################################
# 第六步：MacBook Pro 尺寸选择
########################################

# Pro 14寸 - 修改：只设置stage，不显示选项
RULE product_query_set_pro_14
WHEN INTENT_IS product_query
     AND CONTEXT_EQ current_series = "MacBook Pro"
     AND USER_MENTION_ANY "14|1|第一个|14寸"
     AND CONTEXT_STAGE_IS "config_select"
THEN
    SET_STAGE "chip_select"
    RESPOND_KB "mbp_14_chip_options"

# Pro 16寸 - 修改：只设置stage，不显示选项
RULE product_query_set_pro_16
WHEN INTENT_IS product_query
     AND CONTEXT_EQ current_series = "MacBook Pro"
     AND USER_MENTION_ANY "16|2|3|4|第二个|第三个|第四个|16寸"
     AND CONTEXT_STAGE_IS "config_select"
THEN
    SET_STAGE "chip_select"
    RESPOND_KB "mbp_16_chip_options"

########################################
# 芯片配置选择（在尺寸选择之后）
########################################

# M3芯片选择
RULE product_query_set_chip_m3
WHEN INTENT_IS product_query
     AND CONTEXT_STAGE_IS "chip_select"
     AND USER_MENTION_ANY "1|第一个|m3|M3芯片"
THEN
    SET_STAGE "storage_select"
    RESPOND_KB "mbp_storage_options_m3"

# M3 Pro芯片选择
RULE product_query_set_chip_m3_pro
WHEN INTENT_IS product_query
     AND CONTEXT_STAGE_IS "chip_select"
     AND USER_MENTION_ANY "2|第二个|m3 pro|M3 Pro芯片"
THEN
    SET_STAGE "storage_select"
    RESPOND_KB "mbp_storage_options_m3_pro"

# M3 Max芯片选择
RULE product_query_set_chip_m3_max
WHEN INTENT_IS product_query
     AND CONTEXT_STAGE_IS "chip_select"
     AND USER_MENTION_ANY "3|第三个|m3 max|M3 Max芯片"
THEN
    SET_STAGE "storage_select"
    RESPOND_KB "mbp_storage_options_m3_max"

########################################
# 第七步：存储配置选择
########################################

# 存储选择 - 增强：支持数字选择和具体配置
RULE product_query_set_storage_256
WHEN INTENT_IS product_query
     AND CONTEXT_STAGE_IS "storage_select"
     AND USER_MENTION_ANY "256|1|第一个|选项一|8GB.+256GB|256GB"
THEN
    SET_STAGE "color_select"
    RESPOND "✅ 已选择 8GB + 256GB 配置"
    RESPOND "🎨 MacBook Air 颜色选项："
    RESPOND "1. 深空灰色"
    RESPOND "2. 银色"
    RESPOND "3. 星光色"
    RESPOND "4. 午夜色"
    RESPOND "您喜欢哪种颜色？可以说 1、2、3、4"

RULE product_query_set_storage_512
WHEN INTENT_IS product_query
     AND CONTEXT_STAGE_IS "storage_select"
     AND USER_MENTION_ANY "512|2|第二个|选项二|8GB.+512GB|512GB"
THEN
    SET_STAGE "color_select"
    RESPOND "✅ 已选择 8GB + 512GB 配置"
    RESPOND "🎨 MacBook Air 颜色选项："
    RESPOND "1. 深空灰色"
    RESPOND "2. 银色"
    RESPOND "3. 星光色"
    RESPOND "4. 午夜色"
    RESPOND "您喜欢哪种颜色？可以说 1、2、3、4"

RULE product_query_set_storage_1tb
WHEN INTENT_IS product_query
     AND CONTEXT_STAGE_IS "storage_select"
     AND USER_MENTION_ANY "1tb|1TB|3|第三个|16GB.+1TB"
THEN
    SET_STAGE "color_select"
    RESPOND "✅ 已选择 16GB + 1TB 配置"
    RESPOND "🎨 MacBook Air 颜色选项："
    RESPOND "1. 深空灰色"
    RESPOND "2. 银色"
    RESPOND "3. 星光色"
    RESPOND "4. 午夜色"
    RESPOND "您喜欢哪种颜色？可以说 1、2、3、4"

########################################
# 第八步：颜色选择
########################################

RULE product_query_set_color_gray
WHEN INTENT_IS product_query
     AND CONTEXT_STAGE_IS "color_select"
     AND USER_MENTION_ANY "深空灰|灰色|1|第一个"
THEN
    SET_STAGE "completed"
    RESPOND "✅ 配置完成！您的选择：${product_chain} + 深空灰色"
    RESPOND "💰 总价：根据具体配置定价"
    RESPOND "📦 是否需要加入购物车？还是继续了解其他产品？"

RULE product_query_set_color_silver
WHEN INTENT_IS product_query
     AND CONTEXT_STAGE_IS "color_select"
     AND USER_MENTION_ANY "银色|2|第二个"
THEN
    SET_STAGE "completed"
    RESPOND "✅ 配置完成！您的选择：${product_chain} + 银色"
    RESPOND "💰 总价：根据具体配置定价"
    RESPOND "📦 是否需要加入购物车？还是继续了解其他产品？"

RULE product_query_set_color_starlight
WHEN INTENT_IS product_query
     AND CONTEXT_STAGE_IS "color_select"
     AND USER_MENTION_ANY "星光|星光色|3|第三个"
THEN
    SET_STAGE "completed"
    RESPOND "✅ 配置完成！您的选择：${product_chain} + 星光色"
    RESPOND "💰 总价：根据具体配置定价"
    RESPOND "📦 是否需要加入购物车？还是继续了解其他产品？"

RULE product_query_set_color_midnight
WHEN INTENT_IS product_query
     AND CONTEXT_STAGE_IS "color_select"
     AND USER_MENTION_ANY "午夜|午夜色|4|第四个"
THEN
    SET_STAGE "completed"
    RESPOND "✅ 配置完成！您的选择：${product_chain} + 午夜色"
    RESPOND "💰 总价：根据具体配置定价"
    RESPOND "📦 是否需要加入购物车？还是继续了解其他产品？"

########################################
# 其他品牌闭合处理
########################################

# 手机深度流程：苹果 iPhone
RULE product_query_set_brand_apple_phone
WHEN INTENT_IS product_query
    AND CONTEXT_EQ current_category = "手机"
    AND USER_MENTION_ANY "苹果|apple|iphone"
    AND CONTEXT_STAGE_IS "brand_select"
THEN
    SET_VAR current_brand = "苹果"
    ADD_TO_CHAIN type = "brand" value = "苹果"
    SET_STAGE "phone_model_select"
    SUGGEST_SERIES

RULE product_query_set_phone_model_16pro
WHEN INTENT_IS product_query
    AND CONTEXT_EQ current_category = "手机"
    AND CONTEXT_EQ current_brand = "苹果"
    AND USER_MENTION_ANY "16 pro|16pro|pro max|1|第一个"
    AND CONTEXT_STAGE_IS "phone_model_select"
THEN
    SET_VAR current_series = "iPhone 16 Pro 系列"
    ADD_TO_CHAIN type = "series" value = "iPhone 16 Pro 系列"
    SET_STAGE "phone_storage_select"
    DESCRIBE_SERIES_CONFIG

RULE product_query_set_phone_model_16
WHEN INTENT_IS product_query
    AND CONTEXT_EQ current_category = "手机"
    AND CONTEXT_EQ current_brand = "苹果"
    AND USER_MENTION_ANY "16|16 plus|标准版|2|第二个"
    AND CONTEXT_STAGE_IS "phone_model_select"
THEN
    SET_VAR current_series = "iPhone 16 系列"
    ADD_TO_CHAIN type = "series" value = "iPhone 16 系列"
    SET_STAGE "phone_storage_select"
    DESCRIBE_SERIES_CONFIG

RULE product_query_set_phone_model_15
WHEN INTENT_IS product_query
    AND CONTEXT_EQ current_category = "手机"
    AND CONTEXT_EQ current_brand = "苹果"
    AND USER_MENTION_ANY "15|15 plus|上一代|3|第三个"
    AND CONTEXT_STAGE_IS "phone_model_select"
THEN
    SET_VAR current_series = "iPhone 15 系列"
    ADD_TO_CHAIN type = "series" value = "iPhone 15 系列"
    SET_STAGE "phone_storage_select"
    DESCRIBE_SERIES_CONFIG

RULE product_query_set_phone_storage_128
WHEN INTENT_IS product_query
    AND CONTEXT_STAGE_IS "phone_storage_select"
    AND USER_MENTION_ANY "128|128gb|1|第一个"
THEN
    SET_STAGE "phone_color_select"
    RESPOND_KB "iphone_color_options"

RULE product_query_set_phone_storage_256
WHEN INTENT_IS product_query
    AND CONTEXT_STAGE_IS "phone_storage_select"
    AND USER_MENTION_ANY "256|256gb|2|第二个"
THEN
    SET_STAGE "phone_color_select"
    RESPOND_KB "iphone_color_options"

RULE product_query_set_phone_storage_512
WHEN INTENT_IS product_query
    AND CONTEXT_STAGE_IS "phone_storage_select"
    AND USER_MENTION_ANY "512|512gb|3|第三个"
THEN
    SET_STAGE "phone_color_select"
    RESPOND_KB "iphone_color_options"

RULE product_query_set_phone_storage_1tb
WHEN INTENT_IS product_query
    AND CONTEXT_STAGE_IS "phone_storage_select"
    AND USER_MENTION_ANY "1tb|1024|更大容量"
THEN
    SET_STAGE "phone_color_select"
    RESPOND_KB "iphone_color_options"

RULE product_query_set_phone_color_black
WHEN INTENT_IS product_query
    AND CONTEXT_STAGE_IS "phone_color_select"
    AND USER_MENTION_ANY "黑|黑色|1|第一个"
THEN
    SET_STAGE "completed"
    RESPOND "✅ 配置完成！您的选择：${product_chain} + 黑色"
    RESPOND "💰 价格会根据容量和渠道波动，稍后可为您计算预估价。"
    RESPOND "是否需要加入购物车，还是继续了解其他产品？"

RULE product_query_set_phone_color_white
WHEN INTENT_IS product_query
    AND CONTEXT_STAGE_IS "phone_color_select"
    AND USER_MENTION_ANY "白|白色|2|第二个"
THEN
    SET_STAGE "completed"
    RESPOND "✅ 配置完成！您的选择：${product_chain} + 白色"
    RESPOND "💰 价格会根据容量和渠道波动，稍后可为您计算预估价。"
    RESPOND "是否需要加入购物车，还是继续了解其他产品？"

RULE product_query_set_phone_color_blue
WHEN INTENT_IS product_query
    AND CONTEXT_STAGE_IS "phone_color_select"
    AND USER_MENTION_ANY "蓝|蓝色|3|第三个"
THEN
    SET_STAGE "completed"
    RESPOND "✅ 配置完成！您的选择：${product_chain} + 蓝色"
    RESPOND "💰 价格会根据容量和渠道波动，稍后可为您计算预估价。"
    RESPOND "是否需要加入购物车，还是继续了解其他产品？"

RULE product_query_set_phone_color_natural
WHEN INTENT_IS product_query
    AND CONTEXT_STAGE_IS "phone_color_select"
    AND USER_MENTION_ANY "自然|钛|自然钛|4|第四个"
THEN
    SET_STAGE "completed"
    RESPOND "✅ 配置完成！您的选择：${product_chain} + 自然钛色"
    RESPOND "💰 价格会根据容量和渠道波动，稍后可为您计算预估价。"
    RESPOND "是否需要加入购物车，还是继续了解其他产品？"


# 手机品牌闭合处理（仅针对苹果品牌）
RULE product_query_phone_brand_complete
WHEN INTENT_IS product_query
     AND CONTEXT_EQ current_category = "手机"
     AND USER_MENTION_ANY "苹果|apple|iphone|1|2|3|4"
     AND CONTEXT_STAGE_IS "brand_select"
THEN
    SET_STAGE "completed"
    RESPOND "📱 根据您的选择（${product_chain}），已了解您的苹果手机品牌偏好。"
    RESPOND "目前 iPhone 型号更新较快，价格也会随配置和活动有所浮动。"
    RESPOND "建议您提供具体型号或预算范围，以便为您查询更贴近的价格区间。"

########################################
# 购物车操作
########################################

# 加入购物车
RULE add_to_cart_rule
WHEN INTENT_IS cart_operation
    AND USER_MENTION_ANY "加入购物车|加入|加入购物|加入车|加入购物车吧|加到购物车|放进购物车"
    AND CONTEXT_STAGE_IS "completed"
THEN
    SET_STAGE "cart_added"
    RESPOND "🛒 已成功将 ${product_chain} 加入购物车！"
    RESPOND "📋 当前购物车内容："
    RESPOND "   - ${product_chain}"
    RESPOND "💰 估算总价：根据配置定价"
    RESPOND "下一步您可以："
    RESPOND "1. 继续浏览其他产品"
    RESPOND "2. 查看购物车"
    RESPOND "3. 立即结算"

# 查看购物车
RULE view_cart_rule
WHEN INTENT_IS cart_operation
    AND USER_MENTION_ANY "查看购物车|看购物车|购物车|我的购物车|看看购物车|显示购物车"
THEN
    SET_STAGE "viewing_cart"
    RESPOND "📋 您的购物车内容："
    RESPOND "   - ${product_chain}"
    RESPOND "💰 估算总价：根据配置定价"
    RESPOND "🛒 请选择操作："
    RESPOND "1. 继续购物"
    RESPOND "2. 立即结算"
    RESPOND "3. 清空购物车"

# 立即结算
RULE checkout_rule
WHEN INTENT_IS cart_operation
    AND USER_MENTION_ANY "结算|立即结算|下单|购买|现在买|付款|2|第二个"
THEN
    SET_STAGE "checkout"
    RESPOND "💰 结算页面"
    RESPOND "商品：${product_chain}"
    RESPOND "总价：根据配置定价"
    RESPOND "请提供收货地址和联系方式完成订单"

# 订单确认规则
RULE confirm_order
WHEN INTENT_IS confirmation
    AND CONTEXT_STAGE_IS "checkout"
THEN
    RESPOND "✅ 订单已确认！我们将尽快为您安排发货。"
    RESPOND "📦 您可以在APP中随时查看订单状态和物流信息。"
    RESPOND "👋 感谢您的购买，期待您的使用体验！"
    SET_STAGE "order_completed"

RULE confirm_order_text
WHEN INTENT_IS cart_operation
    AND CONTEXT_STAGE_IS "checkout"
    AND USER_MENTION_ANY "完成订单|确认订单|确认下单|提交订单|下单|确认"
THEN
    RESPOND "✅ 订单已确认！我们将尽快为您安排发货。"
    RESPOND "📦 您可以在APP中随时查看订单状态和物流信息。"
    RESPOND "👋 感谢您的购买，期待您的使用体验！"
    SET_STAGE "order_completed"

# 全局重置（cart_operation 意图场景下）
RULE cart_global_reset_rule
WHEN INTENT_IS cart_operation
    AND USER_MENTION_ANY "重置|重新开始"
THEN
    RESET_SHOPPING_CONTEXT
    RESPOND_KB "restart_prompt_short"


# 继续购物 - 使用完整重置
RULE continue_shopping_rule
WHEN INTENT_IS cart_operation
    AND USER_MENTION_ANY "继续购物|继续浏览|再看看|继续看|浏览其他|继续|1|第一个"
THEN
    RESET_SHOPPING_CONTEXT
    RESPOND_KB "restart_prompt_short"

# 清空购物车 - 使用完整重置
RULE clear_cart_rule
WHEN INTENT_IS cart_operation
    AND USER_MENTION_ANY "清空购物车|清空|删除|移除|3|第三个"
THEN
    RESET_SHOPPING_CONTEXT
    RESPOND_KB "cart_cleared_prompt"
########################################
# 确认性回答处理
########################################

# 确认加入购物车
RULE confirm_add_to_cart
WHEN INTENT_IS confirmation
    AND USER_MENTION_ANY "是|是的|好的|可以|行|没问题|确定|加入|要"
    AND CONTEXT_STAGE_IS "completed"
THEN
    SET_STAGE "cart_added"
    RESPOND "🛒 已成功将 ${product_chain} 加入购物车！"
    RESPOND "📋 当前购物车内容："
    RESPOND "   - ${product_chain}"
    RESPOND "💰 估算总价：根据配置定价"
    RESPOND "👋 感谢您的选择！下一步您可以："
    RESPOND "1. 继续浏览其他产品"
    RESPOND "2. 查看购物车"
    RESPOND "3. 立即结算"

# 确认继续购物
RULE confirm_continue_shopping
WHEN INTENT_IS confirmation
    AND USER_MENTION_ANY "是|是的|好的|可以|行|继续|再看看"
    AND CONTEXT_STAGE_IS "cart_added"
THEN
    SET_STAGE "welcome"
    RESPOND "🔄 好的，让我们重新开始！"
    RESPOND "您想了解什么苹果产品？可以说：Mac、iPhone、iPad 等"

# 否定回答
RULE negative_response
WHEN INTENT_IS confirmation
    AND USER_MENTION_ANY "不|不用|不要|否|不是|不需要"
THEN
    SET_STAGE "welcome"
    RESPOND "👌 好的，了解。"
    RESPOND "您想了解什么其他苹果产品？可以说：Mac、iPhone、iPad 等"
########################################
# 上下文兜底提示（fallback 规则）
########################################

# 大类选择阶段：请用户在电脑/手机之间选择
RULE fallback_category_select
WHEN INTENT_IS fallback
    AND CONTEXT_STAGE_IS "category_select"
THEN
    RESPOND_KB "fallback_category_select_prompt"

# 子类选择阶段：请用户在笔记本/台式机之间选择
RULE fallback_subtype_select
WHEN INTENT_IS fallback
    AND CONTEXT_STAGE_IS "subtype_select"
THEN
    RESPOND_KB "fallback_subtype_select_prompt"

# 品牌选择阶段：优先使用子类，其次使用大类，最后使用通用“产品”
RULE fallback_brand_select_with_subtype
WHEN INTENT_IS fallback
    AND CONTEXT_STAGE_IS "brand_select"
    AND CONTEXT_HAS "current_subtype"
THEN
    RESPOND_KB "fallback_brand_select_with_subtype_prompt"
    SUGGEST_BRANDS

RULE fallback_brand_select_with_category
WHEN INTENT_IS fallback
    AND CONTEXT_STAGE_IS "brand_select"
    AND CONTEXT_NOT_SET current_subtype
    AND CONTEXT_HAS "current_category"
THEN
    RESPOND_KB "fallback_brand_select_with_category_prompt"
    SUGGEST_BRANDS

RULE fallback_brand_select_generic
WHEN INTENT_IS fallback
    AND CONTEXT_STAGE_IS "brand_select"
    AND CONTEXT_NOT_SET current_subtype
    AND CONTEXT_NOT_SET current_category
THEN
    RESPOND_KB "fallback_brand_select_generic_prompt"
    SUGGEST_BRANDS

# 系列选择阶段
RULE fallback_series_select
WHEN INTENT_IS fallback
    AND CONTEXT_STAGE_IS "series_select"
THEN
    RESPOND_KB "fallback_series_select_prompt"
    SUGGEST_SERIES

# 配置选择阶段 - 允许切换到手机类别
RULE product_query_switch_to_phone_from_config
WHEN INTENT_IS product_query
    AND CONTEXT_STAGE_IS "config_select"
    AND USER_MENTION_ANY "手机|iphone|iPhone"
THEN
    SET_VAR current_category = "手机"
    ADD_TO_CHAIN type = "category" value = "手机"
    SET_VAR current_brand = "苹果"
    ADD_TO_CHAIN type = "brand" value = "苹果"
    CLEAR_VAR current_series
    SET_STAGE "series_select"
    RESPOND "好的，我们来看看手机产品！"
    SUGGEST_SERIES

# 配置选择阶段 - 允许切换到电脑类别
RULE product_query_switch_to_computer_from_config
WHEN INTENT_IS product_query
    AND CONTEXT_STAGE_IS "config_select"
    AND USER_MENTION_ANY "电脑|计算机|笔记本|台式机|macbook|mac|Mac"
THEN
    SET_VAR current_category = "电脑"
    ADD_TO_CHAIN type = "category" value = "电脑"
    CLEAR_VAR current_brand
    CLEAR_VAR current_series
    SET_STAGE "subtype_select"
    RESPOND "好的，我们来看看电脑产品！"
    RESPOND_KB "computer_subtype_prompt"

# 配置选择阶段 - 允许切换到平板类别
RULE product_query_switch_to_ipad_from_config
WHEN INTENT_IS product_query
    AND CONTEXT_STAGE_IS "config_select"
    AND USER_MENTION_ANY "iPad|ipad|平板|平板电脑"
THEN
    SET_VAR current_category = "平板"
    ADD_TO_CHAIN type = "category" value = "平板"
    SET_VAR current_brand = "苹果"
    ADD_TO_CHAIN type = "brand" value = "苹果"
    CLEAR_VAR current_series
    SET_STAGE "series_select"
    RESPOND "好的，我们来看看iPad产品！"
    SUGGEST_SERIES

# 通用配置选择规则 - 处理有效的数字输入
RULE product_query_valid_config_choice
WHEN INTENT_IS product_query
    AND CONTEXT_STAGE_IS "config_select"
    AND USER_MENTION_ANY "1|2"
THEN
    SET_STAGE "completed"
    RESPOND "✅ 配置选择完成！"
    RESPOND "🎉 感谢您的选择，如需了解更多详情或选购其他产品，请告诉我。"

# 配置选择阶段
RULE fallback_config_select
WHEN INTENT_IS fallback
    AND CONTEXT_STAGE_IS "config_select"
THEN
    RESPOND_KB "fallback_config_select_prompt"
    DESCRIBE_SERIES_CONFIG

# 苹果手机型号选择阶段
RULE fallback_phone_model_select
WHEN INTENT_IS fallback
    AND CONTEXT_STAGE_IS "phone_model_select"
THEN
    RESPOND_KB "fallback_phone_model_select_prompt"

# 苹果手机容量选择阶段
RULE fallback_phone_storage_select
WHEN INTENT_IS fallback
    AND CONTEXT_STAGE_IS "phone_storage_select"
THEN
    RESPOND_KB "fallback_phone_storage_select_prompt"

# 苹果手机颜色选择阶段
RULE fallback_phone_color_select
WHEN INTENT_IS fallback
    AND CONTEXT_STAGE_IS "phone_color_select"
THEN
    RESPOND_KB "fallback_phone_color_select_prompt"

# 订单完成阶段
RULE fallback_order_completed
WHEN INTENT_IS fallback
    AND CONTEXT_STAGE_IS "order_completed"
THEN
    RESPOND "👋 您的订单已提交完成！"
    RESPOND "📱 可以在APP中查看订单详情和物流状态。"
    RESPOND "🛒 如需购买其他产品，请说'重新开始'或直接告诉我产品名称。"

# 默认兜底提示
RULE fallback_default
WHEN INTENT_IS fallback
THEN
    RESPOND_KB "fallback_default_prompt"



########################################
# 通用：订单、投诉、兜底
########################################

RULE order_rule
WHEN INTENT_IS order_status
THEN
    RESPOND "我来帮您查询订单状态。"
    RESPOND "请提供您的订单号，或者您也可以在 APP 中查看最新物流信息。"

RULE complaint_rule
WHEN INTENT_IS complaint
THEN
    RESPOND "抱歉给您带来不便！"
    RESPOND "请详细描述您遇到的问题，我们会尽快处理。"

# 增强的兜底规则
RULE default_rule
WHEN INTENT_IS unknown
THEN
    RESPOND "抱歉，我没有完全理解您的问题。"
    RESPOND "您可以："
    RESPOND "- 说具体产品名称（如：MacBook Air）"
    RESPOND "- 说选项数字（如：1、2、3）"
    RESPOND "- 重新描述您的需求"