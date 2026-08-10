module adder4(
    input [3:0] a,//3：0表示四位二进制数，0～15
    input [3:0] b,
    output [3:0] sum,
    output      carry
);
assign {carry,sum}=a+b;

endmodule