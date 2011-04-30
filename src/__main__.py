#!/usr/bin/python2

import Tkinter as tk
import tkFont
import threading
import Queue
import engine
import os
import sys


class CrystalApp(tk.Tk):
  TITLE = 'Crystal'
  WIDTH = 500
  HEIGHT = 500
  INPUT_COLOR = '#000000'
  INPUT_BACKGROUND = '#DDDDDD'
  RESULT_COLOR = '#007000'
  COMMENT_COLOR = '#555555'
  PROBLEM_COLOR = '#700000'
  ICON = 'data/crystal.ico'

  def __init__(self, parent=None):
    tk.Tk.__init__(self, parent)

    self.title(CrystalApp.TITLE)
    self.resizable(True, True)
    self.config(background='white')
    try:
      self.iconbitmap(CrystalApp.ICON)
    except:
      # Tkinter doesn't support color icons in Unix. Oh well.
      pass
    self.Position()

    self.prompt = tk.Entry(self)
    self.label = tk.Label(self)
    self.frame = tk.Frame(self)
    self.text = tk.Text(self.frame)
    self.scrollbar = tk.Scrollbar(self.frame)

    self.font = tkFont.Font(self.text, size=12, family='Calibri')

    self.ConfigureWidgets()
    self.ConfigureLayout()
    self.ConfigureTags()

    self.drs = None
    self.thread = None
    self.queue = Queue.Queue()
    
    self.after_idle(self.StartLoadingGrammar)

  def Position(self):
    screen_width = self.winfo_screenwidth()
    screen_height = self.winfo_screenheight()
    
    x = (screen_width - CrystalApp.WIDTH) / 2
    y = (screen_height - CrystalApp.HEIGHT) / 2

    self.geometry('%dx%d+%d+%d' %
                  (CrystalApp.WIDTH, CrystalApp.HEIGHT, x, y))

  def ConfigureLayout(self):
    self.frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    self.prompt.pack(side=tk.RIGHT, fill=tk.X, expand=True)
    self.label.pack(side=tk.LEFT)

    self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    self.text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

  def ConfigureTags(self):
    self.text.tag_configure('input', foreground=CrystalApp.INPUT_COLOR,
                            background=CrystalApp.INPUT_BACKGROUND)
    self.text.tag_configure('result', foreground=CrystalApp.RESULT_COLOR)
    self.text.tag_configure('comment', foreground=CrystalApp.COMMENT_COLOR)
    self.text.tag_configure('problem', foreground=CrystalApp.PROBLEM_COLOR)
    self.text.tag_raise('sel')

  def ConfigureWidgets(self):
    self.frame.config(borderwidth=0)
    self.label.config(font=self.font, background='white', text='>>>')
    self.text.config(font=self.font, borderwidth=0, state=tk.DISABLED,
                     wrap=tk.WORD, selectforeground='white')
    self.prompt.config(font=self.font, background='white', borderwidth=0,
                       disabledbackground='white')
    self.prompt.bind('<Return>', self.Evaluate)
    
    self.scrollbar.config(command=self.text.yview)
    self.text.config(yscrollcommand=self.scrollbar.set)

  def PostMessage(self, text, type):
    assert type in ('input', 'result', 'comment', 'problem', 'divider')
    self.text.config(state=tk.NORMAL)
    self.text.insert(tk.END, text + '\n', type)
    self.text.config(state=tk.DISABLED)
    self.text.yview('moveto', 1.0)

  def StartLoadingGrammar(self):
    self.StartThread(LoadGrammar, (self.queue,))

  def Evaluate(self, _):
    input = self.prompt.get()
    if input == '/reset':
      self.prompt.delete(0, tk.END)
      self.text.config(state=tk.NORMAL)
      self.text.delete(1.0, tk.END)
      self.text.config(state=tk.DISABLED)
      self.drs = None
    else:
      self.StartThread(ProcessStringGateway, (input, self.drs, self.queue))

  def StartThread(self, target, args):
    self.thread = threading.Thread(target=target, args=args)
    self.thread.start()
    
    self.prompt.delete(0, tk.END)
    self.prompt.config(state=tk.DISABLED)
    self.label.config(foreground='gray')
    
    self.after(50, self.CheckQueue)

  def CheckQueue(self):
    while not self.queue.empty():
      command, content, type = self.queue.get_nowait()
      if command == 'post':
        self.PostMessage(content, type)
      elif command == 'update_context':
        self.drs = content
      else:
        self.PostMessage('Got unknown command from child thread.', 'problem')

    if self.thread.isAlive():
      self.after(50, self.CheckQueue)
    else:
      self.prompt.config(state=tk.NORMAL)
      self.label.config(foreground='black')


def ProcessStringGateway(input, drs, queue):
  try:
    engine.ProcessString(input, drs, queue)
  except Exception, e:
    queue.put(('post', 'Error encountered in child thread.', 'problem'))
    raise


def LoadGrammar(queue):
  if not engine.cfg_parser._parser:
    queue.put(('post', 'Loading grammar. This may take a while...', 'comment'))
    engine.cfg_parser.ReloadGrammar()
  queue.put(('post', 'Grammar loaded.', 'comment'))


if __name__ == '__main__':
  if sys.argv[-1] == '--grammar':
    from build import grammar
    print 'Building Grammar'
    grammar.BuildGrammar()
  else:
    app = CrystalApp()
    app.mainloop()
