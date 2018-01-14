#!/usr/bin/env python
from sqlalchemy import MetaData
from sqlalchemy_schemadisplay import create_schema_graph

# create the pydot graph object by autoloading all tables via a bound metadata
# object
graph = create_schema_graph(metadata=MetaData('sqlite:///imods.db'),
        show_datatypes=False, # The image would get nasty big if we'd show the datatypes
        show_indexes=False, # ditto for indexes
        rankdir='LR', # From left to right (instead of top to bottom)
        concentrate=False # Don't try to join the relation lines together
        )
graph.write_png('schema_diagram.png') # write out the file
