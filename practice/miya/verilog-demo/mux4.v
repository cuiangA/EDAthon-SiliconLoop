module mux4(
    input [3:0] in0,
    input [3:0] in1,
    input [3:0] in2,
    input [3:0] in3,
    input [1:0] sel,
    output reg[3:0] y
);

always @(*) begin
    case (sel)
        2'b00:y=in0;
        2'b01:y=in1;
        2'b10:y=in2;
        2'b11:y=in3;
        default:y=4'b0000;
    endcase
end
endmodule