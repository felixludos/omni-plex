from .imports import *

from .tools import *
from .kits import *
from .behaviors import *
from .contexts import *
from .quirks import *
from .quirky import *
from .tools import ToolDecorator as tool



def test_tool():
	@tool('a')
	def f(x):
		return x + 1

	assert f(1) == 2

	@tool('b')
	def g(x, y, z):
		return x + y + z



class TestKit(LoopyKit, MutableKit):
	def __init__(self, *tools: AbstractTool, **kwargs):
		super().__init__(**kwargs)
		self.include(*tools)



class TestCraftyKit(CraftyKit):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._process_crafts()



class TestContext(Cached, Context, TestKit):#, Kit, AbstractContext):
	def tools(self, gizmo: Optional[str] = None) -> Iterator[AbstractTool]:
		if gizmo is None:
			yield from filter_duplicates(chain.from_iterable(map(reversed, self._tools_table.values())))
		else:
			if gizmo not in self._tools_table:
				raise self._MissingGizmoError(gizmo)
			yield from reversed(self._tools_table[gizmo])


#
# def test_kit():
# 	@tool('y')
# 	def f(x):
# 		return x + 1
#
# 	@tool('z')
# 	def g(x, y):
# 		return x + y
#
# 	@tool('y')
# 	def f2(y):
# 		return -y
#
# 	ctx = TestContext(f, g)
#
# 	ctx['x'] = 1
# 	assert ctx['y'] == 2
#
# 	ctx.clear_cache()
# 	ctx.include(f2)
#
# 	ctx['x'] = 1
# 	assert ctx['y'] == -2
#
#
#
#
# class TestCraftyKit(MutableKit, TestCraftyKit):
#
# 	@tool('y')
# 	@staticmethod
# 	def f(x):
# 		return x + 1
#
#
# 	@tool('z')
# 	def g(self, x, y):
# 		return x + y
#
#
# 	@tool('w')
# 	@classmethod
# 	def h(cls, z):
# 		return z + 2
#
#
#
# def test_crafty_kit():
#
# 	assert TestCraftyKit.f(1) == 2
# 	assert TestCraftyKit.h(1) == 3
#
# 	kit = TestCraftyKit()
# 	assert kit.f(1) == 2
# 	assert kit.g(1, 2) == 3
# 	assert kit.h(1) == 3
#
# 	ctx = TestContext(kit)
#
# 	assert list(ctx.gizmos()) == ['y', 'z', 'w']
#
# 	ctx['x'] = 1
# 	assert ctx['y'] == 2
# 	ctx['y'] = 3
# 	assert ctx['y'] == 3
# 	assert ctx['z'] == 4
# 	assert ctx['w'] == 6
#
# 	ctx.clear_cache()
# 	ctx['x'] = 10
# 	assert ctx['z'] == 21
# 	assert ctx['w'] == 23
#
#
#
# class TestCraftyKit2(TestCraftyKit): # by default inherits all tools from the parents
# 	def __init__(self, sign=1):
# 		super().__init__()
# 		self._sign = sign
#
#
# 	@tool('y') # tool replaced
# 	def change_y(self, y): # "refinement" - chaining the tool implicitly
# 		return y + 10
#
#
# 	@tool('x') # new tool added
# 	def get_x(self):
# 		return 100 * self._sign # freely use object attributes
#
#
# 	def check(self): # freely calling tools as methods
# 		return self.f(9) + type(self).h(8) + type(self).f(19) # 40
#
#
# 	def g(self, x): # overriding a tool (this will be registered, rather than the super method)
# 		# use with caution - it's recommended to use clear naming for the function
# 		return super().g(x, x) # super method can be called as usual
#
#
#
# def test_crafty_kit_inheritance():
#
# 	assert TestCraftyKit2.f(1) == 2
# 	assert TestCraftyKit2.h(1) == 3
#
# 	kit = TestCraftyKit2()
# 	assert kit.f(1) == 2
# 	assert kit.g(2) == 4
# 	assert kit.h(1) == 3
# 	assert kit.check() == 40
# 	assert kit.get_x() == 100
# 	assert kit.change_y(1) == 11
#
# 	ctx = TestContext(kit)
#
# 	assert list(ctx.gizmos()) == ['y', 'z', 'w', 'x']
#
# 	assert ctx['x'] == 100
# 	assert ctx['y'] == 111
# 	assert ctx['z'] == 200
# 	assert ctx['w'] == 202
#
# 	ctx.clear_cache()
#
# 	@tool('z')
# 	def new_z():
# 		return 1000
#
# 	ctx.include(new_z)
#
# 	assert 'x' not in ctx.cached()
# 	assert ctx['y'] == 111
# 	assert 'x' in ctx.cached()
# 	assert ctx['x'] == 100
#
# 	assert ctx['z'] == 1000
# 	assert ctx['w'] == 1002



class LambdaTool(AbstractTool):
	def __init__(self, fn, inp='input', out='output', **kwargs):
		if isinstance(inp, str):
			inp = [inp]
		super().__init__(**kwargs)
		self.fn = fn
		self.input_keys = inp
		self.output_key = out


	def __call__(self, *args, **kwargs):
		return self.fn(*args, **kwargs)


	def gizmos(self) -> Iterator[str]:
		yield self.output_key


	def get_from(self, ctx: Optional[AbstractContext], gizmo: str,
	             default: Optional[Any] = unspecified_argument) -> Any:
		inputs = [ctx[g] for g in self.input_keys]
		return self.fn(*inputs)



class trait(AppliedTrait, SimpleQuirk):
	pass



class SuperModule(TestCraftyKit, Capable):
	augmentation = trait(apply={'input': 'x', 'output': 'x'})
	model = trait(apply={'input': 'x', 'output': 'y'})



def test_trait():

	sup = SuperModule(augmentation=LambdaTool(lambda x: x + 1),
	                  model=LambdaTool(lambda x: x * 2))

	ctx = TestContext(sup)

	assert list(ctx.gizmos()) == ['x', 'y']

	@tool('x')
	def gen_x():
		return 1

	ctx = TestContext(gen_x, sup)

	assert ctx['y'] == 4 # not 3, because the augmentation is applied first

	print(ctx)












