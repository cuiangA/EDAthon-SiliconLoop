`timescale 1ns/1ps

module tb_counter4;

reg        clk;
reg        reset;
wire [3:0] count;
integer    expected;
integer    i;

counter4 dut (
    .clk   (clk),
    .reset (reset),
    .count (count)
);

// Generate a clock with a 10 ns period.
initial clk = 1'b0;
always #5 clk = ~clk;

initial begin
    $dumpfile("counter4.vcd");
    $dumpvars(0, tb_counter4);

    // Hold reset high across the first rising clock edge.
    reset = 1'b1;
    @(posedge clk);
    #1;
    if (count !== 4'd0)
        $fatal(1, "RESET FAILED: expected 0, got %0d", count);

    // Release reset away from an active clock edge.
    @(negedge clk);
    reset = 1'b0;

    // Check 16 increments, including wraparound from 15 to 0.
    for (i = 1; i <= 16; i = i + 1) begin
        @(posedge clk);
        #1;
        expected = i % 16;
        if (count !== expected[3:0])
            $fatal(1, "COUNT FAILED: cycle=%0d expected=%0d got=%0d",
                   i, expected, count);
        $display("cycle=%0d count=%0d", i, count);
    end

    $display("ALL TESTS PASSED");
    $finish;
end

endmodule
