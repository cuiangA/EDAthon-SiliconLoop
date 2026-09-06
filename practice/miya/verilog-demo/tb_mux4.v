module tb_mux4;

reg  [3:0] in0;
reg  [3:0] in1;
reg  [3:0] in2;
reg  [3:0] in3;
reg  [1:0] sel;
wire [3:0] y;

integer errors;
integer i;
reg [3:0] expected;

mux4 uut (
    .in0(in0),
    .in1(in1),
    .in2(in2),
    .in3(in3),
    .sel(sel),
    .y(y)
);

task check;
    begin
        case (sel)
            2'b00: expected = in0;
            2'b01: expected = in1;
            2'b10: expected = in2;
            2'b11: expected = in3;
            default: expected = 4'b0000;
        endcase

        #1;

        if (y !== expected) begin
            $display(
                "FAIL: in0=%d in1=%d in2=%d in3=%d sel=%b expected=%d actual=%d",
                in0, in1, in2, in3, sel, expected, y
            );
            errors = errors + 1;
        end else begin
            $display("PASS: sel=%b y=%d", sel, y);
        end
    end
endtask

initial begin
    $dumpfile("mux4.vcd");
    $dumpvars(0, tb_mux4);

    errors = 0;

    // Fixed tests
    in0 = 4'd1;
    in1 = 4'd3;
    in2 = 4'd7;
    in3 = 4'd15;

    sel = 2'b00;
    check();

    sel = 2'b01;
    check();

    sel = 2'b10;
    check();

    sel = 2'b11;
    check();

    // Random tests
    for (i = 0; i < 100; i = i + 1) begin
        in0 = $random;
        in1 = $random;
        in2 = $random;
        in3 = $random;
        sel = $random;
        check();
    end

    if (errors == 0)
        $display("ALL TESTS PASSED");
    else
        $display("TEST FAILED: %d error(s)", errors);

    $finish;
end

endmodule