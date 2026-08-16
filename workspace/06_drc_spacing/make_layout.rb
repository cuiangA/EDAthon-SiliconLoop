layout = RBA::Layout::new
layout.dbu = 0.001

top = layout.create_cell("TOP")
m1 = layout.layer(1, 0)

# Coordinates are in database units. With dbu = 0.001 um, 1 unit = 0.001 um.
# The rectangles satisfy M1 width >= 0.05 um and spacing >= 0.06 um.
top.shapes(m1).insert(RBA::Box::new(0, 0, 60, 200))
top.shapes(m1).insert(RBA::Box::new(130, 0, 190, 200))

layout.write("layout.gds")
puts "Wrote layout.gds"
