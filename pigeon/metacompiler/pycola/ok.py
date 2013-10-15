from string import whitespace
import sys
from nonon import (
  symbol as SYM,
  literal as LIT,
  list_ as LIST,
  send,
  print_context,
  eval_context,
  )


class Context:

  def __init__(self, text):
    self.stream = iter(text)
    self.advance()
    self.success = True
    self.current_frame = []
    self.frame_stack = []

  def advance(self):
    self.collect()
    try:
      self.current = self.stream.next()
    except StopIteration:
      if not self.success:
        raise

  def collect(self):
    if hasattr(self, 'basket') and self.basket is not None:
      self.basket.append(self.current)

  def push(self, term):
    self.current_frame.append(term)

  def __repr__(self):
    return '<Context %r %s >' % (self.current, self.success)


def deco(f):
  def chk(context):
    if context.success: f(context)
  return chk


def chartok(char):
  @deco
  def tok(context):
    if context.current == char:
      print >> sys.stderr, char, context
      context.advance()
    else:
      context.success = False
  return tok


def rangetok(start, stop):
  @deco
  def tok(context):
    if start <= context.current <= stop:
      print >> sys.stderr, start, '-', stop, context
      context.advance()
    else:
      context.success = False
  return tok


class PopFrame(Exception): pass


def OR(context):
  if context.success:
    raise PopFrame
  context.success = True


def seq(*terms):
  @deco
  def do_seq(context):
    try:
      for term in terms: term(context)
    except PopFrame:
      pass
  return do_seq


def kstar(term):
  @deco
  def kst(context):
    while context.success: term(context)
    context.success = True
  return kst


def parse(text, pattern):
  context = Context(text)
  pattern(context)
  return context


def capture(f, post_process=eval):
  @deco
  def bracket(context):
    b = context.basket = []
    f(context)
    if context.success:
      found = ''.join(b)
      found = post_process(found)
      context.push(found)
    context.basket = None
  return bracket


@deco
def start_frame(context):
  new_frame = []
  context.frame_stack.append(context.current_frame)
  context.current_frame = new_frame


@deco
def finish_frame(context):
  frame = context.frame_stack.pop()
  frame.append(LIST(*context.current_frame))
  context.current_frame = frame


blanc = [OR] * (len(whitespace) * 2 - 1)
blanc[::2] = map(chartok, whitespace) #Python is cool. ;)
blanc = seq(*blanc)
__ = kstar(blanc)
lparen, rparen = chartok('('), chartok(')')
dot = chartok('.')
quote = chartok("'")
low = rangetok('a', 'z')
high = rangetok('A', 'Z')
letter = seq(low, OR, high)
digit = rangetok('0', '9')
number = capture(seq(digit, kstar(digit)), lambda i: LIT(int(i)))
anychar = kstar(seq(letter, OR, digit))
symbol = capture(seq(letter, anychar), SYM)
string = capture(seq(quote, anychar, quote), lambda i: LIT(eval(i)))
term = seq(number, OR, symbol, OR, string)
@deco
def do_list(context):
  seq(
    lparen, __, start_frame,
    kstar(seq(seq(term, OR, do_list), __)),
    rparen, finish_frame
    )(context)


little_language = seq(__, kstar(seq(do_list, __)), dot)


c = Context(''' ( 123 a (bb c 34))  ('Tuesday')
   (define p (divide 1 1000000000))
   (define pi (multiply 3141592653 p))
   (pi p)
   (define area (lambda (r) (multiply pi (multiply r r))))
   ( area 23 nic )
   ( 12 'neato' )

.''')

little_language(c)
print c
print

for it in c.current_frame:
  send(it, 'eval', print_context)
  print
print

print 'Evaluating...' ; print
for it in c.current_frame:
  send(it, 'eval', eval_context)
print

send(eval_context, 'addMethod', 'multiply', lambda x, y: y * x)
send(eval_context, 'addMethod', 'divide', lambda x, y: x / float(y))
print 'Evaluating...' ; print
for it in c.current_frame:
  send(it, 'eval', eval_context)
