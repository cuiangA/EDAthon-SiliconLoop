module tb_ppa_factor;

reg  [7:0] a;
reg  [7:0] b;
reg  [7:0] c;
wire [7:0] y_ref;
wire [7:0] y_target;

ppa_reference u_ref (
    .a(a),
    .b(b),
    .c(c),
    .y(y_ref)
);

ppa_target u_target (
    .a(a),
    .b(b),
    .c(c),
    .y(y_target)
);

integer i;

task check_case;
    input [7:0] ta;
    input [7:0] tb;
    input [7:0] tc;
    begin
        a = ta;
        b = tb;
        c = tc;
        #1;
        if (y_target !== y_ref) begin
            $display("FAIL: a=%02h b=%02h c=%02h expected=%02h actual=%02h",
                     a, b, c, y_ref, y_target);
            $fatal(1, "functional mismatch");
        end
    end
endtask

initial begin
    check_case(8'h00, 8'h00, 8'h00);
    check_case(8'hff, 8'h00, 8'hff);
    check_case(8'ha5, 8'h0f, 8'h33);
    check_case(8'h3c, 8'hc3, 8'h55);

    for (i = 0; i < 64; i = i + 1) begin
        check_case((i * 8'h25) ^ 8'ha5,
                   (i * 8'h13) ^ 8'h5a,
                   (i * 8'h07) ^ 8'hc3);
    end

    $display("PASS: ppa_target is functionally equivalent to ppa_reference");
    $finish;
end

endmodule
