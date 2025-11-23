import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.form_based_system import FormBasedDialogSystem
from semantics.option_mapping import SemanticMapper


def test_size_numeric_selection():
    form = FormBasedDialogSystem('apple_store')
    llm = None
    semantic = SemanticMapper()
    # 模拟已提示尺寸槽位
    form.last_prompted_slot = 'size'
    form.process_input('2', llm, semantic)  # 选择 14寸
    assert form.current_form['size'].value is not None
    assert form.current_form['size'].value.value == '14寸'


def test_size_unique_text_match():
    form = FormBasedDialogSystem('apple_store')
    llm = None
    semantic = SemanticMapper()
    form.last_prompted_slot = 'size'
    form.process_input('我想要16英寸', llm, semantic)
    assert form.current_form['size'].value is not None
    assert form.current_form['size'].value.value == '16寸'
