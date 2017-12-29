# Chain Constructor for java

Thanks to /jacobsimpson/nvim-example-python-plugin for the neovim plugin template.


### Installation

Using <a href="https://github.com/Shougo/dein.vim">dein</a>
```Bash
    call dein#add('dominic-dev/nvim-jchain')
```

Using NeoBundle
```Bash
    NeoBundle 'dominic-dev/nvim-jchain'
```

### <a id="python_version"></a>Python Version

This plugin code works with Python 3.
```Python
pip3 install neovim
```

### Usage 
#### ChainConstructor
```VimL
:ChainConstructor
```
Insert the call to another constructor, with the apropriate variables.


#### ChainSuper
```VimL
:ChainSuper
```
Insert the call to a super constructor, with the apropriate variables.

#### GenerateConstructor
```VimL
:GenerateConstructor
```
 
TODO
Documentation needed.
 

### Settings
For same level constructors no-arg constructors are excluded by default.
To change this behaviour include:
```VimL
let g:jchain_include_noargs = 1
```
in your init.vim file
