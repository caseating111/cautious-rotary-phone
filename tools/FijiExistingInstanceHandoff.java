import net.imagej.legacy.SingleInstance;
import org.scijava.log.StderrLogService;

public class FijiExistingInstanceHandoff {
    public static void main(String[] args) {
        if (args.length != 2) {
            System.err.println("usage: FijiExistingInstanceHandoff <port> <macro-path>");
            System.exit(2);
        }
        int port = Integer.parseInt(args[0]);
        boolean sent = new SingleInstance(port, new StderrLogService(), null).sendArguments(
            new String[] {"-macro", args[1]}
        );
        if (!sent) {
            System.err.println("Fiji existing-instance RMI handoff failed");
            System.exit(3);
        }
    }
}
