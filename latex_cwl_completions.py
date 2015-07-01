# -*- coding:utf-8 -*-
import sublime
import sublime_plugin
import os
import re
import codecs

index = 0

if sublime.version() < '3000':
    # we are on ST2 and Python 2.X
    _ST3 = False
    from latex_cite_completions import OLD_STYLE_CITE_REGEX, NEW_STYLE_CITE_REGEX, match
    from latex_ref_completions import OLD_STYLE_REF_REGEX, NEW_STYLE_REF_REGEX
    from getRegion import get_Region
else:
    _ST3 = True
    from .latex_cite_completions import OLD_STYLE_CITE_REGEX, NEW_STYLE_CITE_REGEX, match
    from .latex_ref_completions import OLD_STYLE_REF_REGEX, NEW_STYLE_REF_REGEX
    from .getRegion import get_Region

# Do not do completions in these envrioments
ENV_DONOT_AUTO_COM = [
    OLD_STYLE_CITE_REGEX,
    NEW_STYLE_CITE_REGEX,
    OLD_STYLE_REF_REGEX,
    NEW_STYLE_REF_REGEX,
    re.compile(r'\\\\')
]

CWL_COMPLETION = False

class LatexCwlCompletion(sublime_plugin.EventListener):

    def on_query_completions(self, view, prefix, locations):
        # settings = sublime.load_settings("LaTeXTools.sublime-settings")
        # cwl_completion = settings.get('cwl_completion')

        if not CWL_COMPLETION:
            return []

        point = locations[0]
        if not view.score_selector(point, "text.tex.latex"):
            return []

        point = locations[0]
        line = view.substr(get_Region(view.line(point).a, point))
        line = line[::-1]

        # Do not do completions in actions
        for rex in ENV_DONOT_AUTO_COM:
            if match(rex, line) != None:
                return []

        completions = parse_cwl_file()
        return (completions, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

    # This functions is to determine whether LaTeX-cwl is installed,
    # if so, trigger auto-completion in latex buffers by '\'
    def on_activated(self, view):
        point = view.sel()[0].b
        if not view.score_selector(point, "text.tex.latex"):
            return

        # Checking whether LaTeX-cwl is installed
        global CWL_COMPLETION
        if os.path.exists(sublime.packages_path() + "/LaTeX-cwl") or \
            os.path.exists(sublime.installed_packages_path() + "/LaTeX-cwl.sublime-package"):
            CWL_COMPLETION = True

        if CWL_COMPLETION:
            g_settings = sublime.load_settings("Preferences.sublime-settings")
            acts = g_settings.get("auto_complete_triggers", [])

            # Whether auto trigger is already set in Preferences.sublime-settings
            TEX_AUTO_COM = False
            for i in acts:
                if i.get("selector") == "text.tex.latex" and i.get("characters") == "\\":
                    TEX_AUTO_COM = True

            if not TEX_AUTO_COM:
                acts.append({
                    "characters": "\\",
                    "selector": "text.tex.latex"
                })
                g_settings.set("auto_complete_triggers", acts)

def parse_cwl_file():
    # Get cwl file list
    # cwl_path = sublime.packages_path() + "/LaTeX-cwl"
    settings = sublime.load_settings("LaTeXTools.sublime-settings")
    view = sublime.active_window().active_view()
    cwl_file_list = view.settings().get('cwl_list',
        settings.get(
            'cwl_list',
            [
                "tex.cwl",
                "latex-209.cwl",
                "latex-document.cwl",
                "latex-l2tabu.cwl",
                "latex-mathsymbols.cwl"
            ]))

    # ST3 can use load_resource api, while ST2 do not has this api
    # so a little different with implementation of loading cwl files.
    if _ST3:
        cwl_files = ['Packages/LaTeX-cwl/%s' % x for x in cwl_file_list]
    else:
        cwl_files = [os.path.normpath(sublime.packages_path() + "/LaTeX-cwl/%s" % x) for x in cwl_file_list]

    completions = []
    for cwl in cwl_files:
        if _ST3:
            s = sublime.load_resource(cwl)
        else:
            f = codecs.open(cwl, 'r', 'utf-8')
            try:
                s = u''.join(f.readlines())
            finally:
                f.close()

        for line in s.split('\n'):
            if line == '':
                continue
            if line.lstrip()[0] == '#':
                continue

            keyword = line.strip()
            method = os.path.splitext(os.path.basename(cwl))[0]
            item = (u'%s\t%s' % (keyword, method), parse_keyword(keyword))
            completions.append(item)

    return completions


def parse_keyword(keyword):
    # Replace strings in [] and {} with snippet syntax
    def replace_braces(matchobj):
        global index
        index += 1
        if matchobj.group(1) != None:
            word = matchobj.group(1)
            return u'{${%d:%s}}' % (index, word)
        else:
            word = matchobj.group(2)
            return u'[${%d:%s}]' % (index, word)

    replace, n = re.subn(r'\{([^\{\}\[\]]*)\}|\[([^\{\}\[\]]*)\]', replace_braces, keyword[1:])

    # I do not understand why some of the input will eat the '\' charactor before it!
    # This code is to avoid these things.
    if n == 0 and re.search(r'^[a-zA-Z]+$', keyword[1:].strip()) != None:
            return keyword
    else:
        return replace
