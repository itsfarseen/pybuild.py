## pybuild.py
~300 line lightweight wrapper for requirements.txt

### Features
* Keep track of direct dependencies.
* Automatically remove unused indirect dependencies.

### How to use

* Copy `pybuild.py` to your project folder.
* Run `./pybuild.py init <venv-folder>`
* If you're migrating an existing project:
  * Add your direct dependencies to `pypackages.json`
  * Run `./pybuild.py sync`.
 
### Project Status

The feature set is kept deliberately small.  
It should be possible to read and understand the entire code in one sitting.  

Bug reports and feature requests are welcome.  
Feature requests are accepted only if they are simple to implement and provide really good value.
