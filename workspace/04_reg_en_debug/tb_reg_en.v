module tb_reg_en;

reg clk;
reg rst_n;
reg en;
reg [7:0] d;
wire [7:0] q;

reg_en dut (
    .clk(clk),
    .rst_n(rst_n),
    .en(en),
    .d(d),
    .q(q)
);

initial begin
    clk = 0;
    forever #5 clk = ~clk;
end

task check;
    input [7:0] expected;
    input [255:0] name;
    begin
        if (q !== expected) begin
            $display("FAIL: %0s expected=%02h actual=%02h time=%0t", name, expected, q, $time);
            $fatal(1, "check failed");
        end
    end
endtask

initial begin
    rst_n = 1;
    en = 0;
    d = 8'h00;

    rst_n = 0;
    en = 1;
    d = 8'ha5;
    @(posedge clk);
    #1;
    check(8'h00, "sync reset has priority over enable");

    rst_n = 1;
    en = 1;
    d = 8'h3c;
    @(posedge clk);
    #1;
    check(8'h3c, "load when enable high");

    en = 0;
    d = 8'hf0;
    @(posedge clk);
    #1;
    check(8'h3c, "hold when enable low");

    rst_n = 0;
    en = 0;
    d = 8'hff;
    @(posedge clk);
    #1;
    check(8'h00, "reset when enable low");

    $display("PASS: reg_en");
    $finish;
end

endmodule
