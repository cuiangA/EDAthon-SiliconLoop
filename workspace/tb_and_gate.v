`timescale 1ns/1ps

module tb_and_gate;

reg a;
reg b;
wire y;

and_gate dut (
    .a(a),
    .b(b),
    .y(y)
);

initial begin
    a = 0; b = 0; #1;
    if (y !== 0) $fatal(1, "00 failed");

    a = 0; b = 1; #1;
    if (y !== 0) $fatal(1, "01 failed");

    a = 1; b = 0; #1;
    if (y !== 0) $fatal(1, "10 failed");

    a = 1; b = 1; #1;
    if (y !== 1) $fatal(1, "11 failed");

    $display("PASS: all tests passed");
    $finish;
end

endmodule