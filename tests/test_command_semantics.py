import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.form_based_system import FormBasedDialogSystem, OrderStatus, SlotStatus
from semantics.option_mapping import SemanticMapper

# 命令语义测试: reselect / restart / confirm


def _fill_minimal_apple(form):
    mapper = SemanticMapper()
    form.process_input('电脑', None, mapper)
    form.process_input('苹果', None, mapper)
    form.process_input('MacBook Pro', None, mapper)
    return mapper


def test_apple_confirm_and_restart():
    form = FormBasedDialogSystem('apple_store')
    mapper = _fill_minimal_apple(form)
    # 达到 READY_CONFIRM 状态
    assert form.order_status == OrderStatus.READY_CONFIRM
    # 确认下单
    resp = form.process_input('确认', None, mapper)
    assert form.order_confirmed is True
    assert form.order_status == OrderStatus.AWAITING_CONTINUE
    assert '✅' in resp['response'] or '订单已确认' in resp['response']
    # 继续购物（restart）
    resp2 = form.process_input('继续购物', None, mapper)
    assert form.order_confirmed is False
    assert form.order_status == OrderStatus.COLLECTING
    # 第一个必填槽位重新提示
    assert form.last_prompted_slot in ['category', 'brand', 'series']


def test_apple_reselect_flow():
    form = FormBasedDialogSystem('apple_store')
    mapper = _fill_minimal_apple(form)
    assert form.order_status == OrderStatus.READY_CONFIRM
    # 触发重选
    resp = form.process_input('重选', None, mapper)
    assert '请选择' in resp['response'] or '修改' in resp['response'] or '想改哪' in resp['response']
    assert form.reselect_slot == 'waiting'
    # 选择第1项 (category)
    form.process_input('1', None, mapper)
    # 重新输入新类别 手机
    form.process_input('手机', None, mapper)
    # 重新输入系列 iPhone 16 系列
    form.process_input('iPhone 16 系列', None, mapper)
    # READY_CONFIRM 再次出现
    assert form.order_status == OrderStatus.READY_CONFIRM
    # 再次确认
    form.process_input('确认', None, mapper)
    assert form.order_confirmed is True


def test_dining_confirm_flow():
    form = FormBasedDialogSystem('dining')
    mapper = SemanticMapper()
    form.process_input('餐饮预订', None, mapper)
    form.process_input('海底捞', None, mapper)
    form.process_input('晚餐时段', None, mapper)
    form.process_input('4人', None, mapper)
    form.process_input('明天', None, mapper)
    form.process_input('13800000000', None, mapper)  # 联系方式自由文本
    # 达到确认状态
    assert form.order_status == OrderStatus.READY_CONFIRM
    resp = form.process_input('确认', None, mapper)
    assert form.order_confirmed is True
    assert form.order_status == OrderStatus.AWAITING_CONTINUE
    # 结束对话
    bye = form.process_input('再见', None, mapper)
    assert bye.get('should_exit') is True

if __name__ == '__main__':
    test_apple_confirm_and_restart()
    test_apple_reselect_flow()
    test_dining_confirm_flow()
    print('command semantics tests passed')
