namespace Worker;

public interface IWorkerEmitter
{
    void EmitSuccess(string json);
    void EmitError(string json);
}
