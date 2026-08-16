module ppa_baseline (
    input  wire [7:0] a,
    input  wire [7:0] b,
    input  wire [7:0] c,
    output wire [7:0] y
);

(* keep *) wire [7:0] ab_path;
(* keep *) wire [7:0] ac_path;

assign ab_path = a & b;
assign ac_path = a & c;
assign y = ab_path | ac_path;

endmodule
