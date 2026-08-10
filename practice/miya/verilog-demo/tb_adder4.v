module tb_adder4;
reg  [3:0] a;
reg  [3:0] b;
wire [3:0] sum;
wire       carry;

integer errors;
adder4 uut(
    .a(a),
    .b(b),
    .sum(sum),
    .carry(carry)
);

task check;
    input [3:0] test_a;
    input [3:0] test_b;
    reg   [4:0] expected;

    begin
        a=test_a;
        b=test_b;
        expected=test_a+test_b;
        #10;

        if({carry,sum} != expected) begin
            $display(
                "FAIL:a=%d b=%d expected=%d actual=%d",
                a,b,expected,{carry,sum}
            );
            errors=errors+1;
        end 
        else begin
            $display(
                "PASS:a=%d b=%d result=%d",
                a,b,{carry,sum}
            );
        end
    end
endtask

initial begin
    $dumpfile("adder4.vcd");
    $dumpvars(0,tb_adder4);

    errors=0;

    check(4'd2,4'd3);
    check(4'd7,4'd8);
    check(4'd15,4'd1);
    check(4'd15,4'd15);

    if(errors==0)
        $display("ALL TESTS PASSED");
    else
        $display("TEST FAILED:%d error(s)",errors);
    $finish;
end
endmodule