`timescale 1ns/1ps

module tb_fsm4;

    reg        clk   = 0;
    reg        rst_n = 0;
    reg        start = 0;
    reg  [7:0] data_in = 8'hA5;
    wire       done;
    wire [7:0] data_out;
    wire [1:0] state;

    integer errors = 0;

    fsm4 dut (
        .clk      (clk),
        .rst_n    (rst_n),
        .start    (start),
        .data_in  (data_in),
        .done     (done),
        .data_out (data_out),
        .state    (state)
    );

    // 10 ns 时钟
    always #5 clk = ~clk;

    // 等一个时钟沿后采样，检查 state 和 done
    task check(input [1:0] exp_state, input exp_done, input string label);
        @(posedge clk);
        #1;
        if (state !== exp_state || done !== exp_done) begin
            $display("FAIL %s: state=%b (期望 %b) done=%b (期望 %b)",
                     label, state, exp_state, done, exp_done);
            errors = errors + 1;
        end else begin
            $display("PASS %s: state=%b done=%b", label, state, done);
        end
    endtask

    initial begin
        $dumpfile("fsm4.vcd");
        $dumpvars(0, tb_fsm4);

        // 复位 3 个周期
        repeat (3) @(posedge clk);
        rst_n = 1;

        // 1. IDLE 保持
        check(2'b00, 1'b0, "idle");

        // 2. start -> LOAD（同时装载 data_in）
        start = 1;
        check(2'b01, 1'b0, "load");
        start = 0;

        // 3. LOAD -> RUN
        check(2'b10, 1'b0, "run-0");

        // 4-6. RUN 中计数 0..2
        check(2'b10, 1'b0, "run-1");
        check(2'b10, 1'b0, "run-2");
        check(2'b10, 1'b0, "run-3");

        // 7. 第 4 个 RUN 周期后 -> DONE，done 拉高
        check(2'b11, 1'b1, "done");

        // 8. DONE -> IDLE，done 拉低；数据保持
        check(2'b00, 1'b0, "idle-again");
        if (data_out !== 8'hA5) begin
            $display("FAIL data_out=%h (期望 a5)", data_out);
            errors = errors + 1;
        end else begin
            $display("PASS data_out=%h", data_out);
        end

        // 9. 第二次运行
        start = 1;
        check(2'b01, 1'b0, "load-2");
        start = 0;

        // 10. 在 RUN 中异步复位，应回到 IDLE
        check(2'b10, 1'b0, "run-2nd");
        rst_n = 0;
        #1;
        check(2'b00, 1'b0, "reset-idle");
        rst_n = 1;

        if (errors == 0)
            $display("ALL TESTS PASSED");
        else
            $display("%0d TEST(S) FAILED", errors);
        $finish;
    end

    // 超时保护
    initial begin
        #1000;
        $display("TIMEOUT!");
        $finish;
    end

endmodule
