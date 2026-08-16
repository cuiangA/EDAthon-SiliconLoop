layout = RBA::Layout::new
layout.dbu = 0.001

top = layout.create_cell("TOP")
m1 = layout.layer(1, 0)

# Coordinates are in database units. With dbu = 0.001 um, 1 unit = 0.001 um.
# These rectangles intentionally violate the provided width and spacing rules.
top.shapes(m1).insert(RBA::Box::new(0, 0, 40, 200))
top.shapes(m1).insert(RBA::Box::new(70, 0, 110, 200))

layout.write("layout_bad.gds")
puts "Wrote layout_bad.gds"
