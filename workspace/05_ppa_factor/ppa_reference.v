module ppa_reference (
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire [7:0] c,
    output wire [7:0] y
);

assign y = (a & b) | (a & c);

endmodule
